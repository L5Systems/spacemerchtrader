"""Starfall Galactic Bank — accounts, deposits, withdrawals, and transfers."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from starfall.game import get_or_create_profile
from starfall.models import BankAccount, BankTransaction, BankTransactionType, Client, PlayerProfile

BANK_NAME = "Starfall Galactic Bank"
MIN_AMOUNT = 0.01


def _touch(record) -> None:
    record.updated_at = datetime.now(timezone.utc)


def _account_number_for(client_id: str) -> str:
    return f"SF-{client_id.replace('-', '').upper()[:10]}"


def get_or_create_bank_account(db: Session, client_id: str) -> BankAccount:
    account = db.get(BankAccount, client_id)
    if account:
        return account

    account = BankAccount(
        client_id=client_id,
        account_number=_account_number_for(client_id),
        balance=0.0,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def account_summary(db: Session, client_id: str) -> dict[str, Any]:
    profile = get_or_create_profile(db, client_id)
    account = get_or_create_bank_account(db, client_id)
    client = db.get(Client, client_id)
    return {
        "account_number": account.account_number,
        "bank_balance": round(account.balance, 2),
        "wallet_credits": round(profile.credits, 2),
        "total_liquid": round(account.balance + profile.credits, 2),
        "holder_name": client.display_name if client else "Unknown",
        "bank_name": BANK_NAME,
    }


def list_recent_transactions(db: Session, client_id: str, limit: int = 8) -> list[dict[str, Any]]:
    account = get_or_create_bank_account(db, client_id)
    rows = (
        db.query(BankTransaction)
        .filter(BankTransaction.account_id == account.client_id)
        .order_by(BankTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "type": row.transaction_type.value,
            "amount": round(row.amount, 2),
            "counterparty_account": row.counterparty_account,
            "memo": row.memo,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def _record_transaction(
    db: Session,
    *,
    account_id: str,
    transaction_type: BankTransactionType,
    amount: float,
    counterparty_client_id: str | None = None,
    counterparty_account: str | None = None,
    memo: str = "",
) -> BankTransaction:
    tx = BankTransaction(
        id=str(uuid.uuid4()),
        account_id=account_id,
        transaction_type=transaction_type,
        amount=round(amount, 2),
        counterparty_client_id=counterparty_client_id,
        counterparty_account=counterparty_account,
        memo=memo,
    )
    db.add(tx)
    return tx


def _game_result(profile: PlayerProfile, detail: str) -> dict[str, Any]:
    return {
        "total_credits": round(profile.credits, 2),
        "outcome_detail": detail,
    }


def deposit(db: Session, client_id: str, amount: float) -> dict[str, Any]:
    if amount < MIN_AMOUNT:
        raise ValueError("Deposit amount must be at least 0.01 credits")

    profile = get_or_create_profile(db, client_id)
    account = get_or_create_bank_account(db, client_id)
    if profile.credits < amount:
        raise ValueError(
            f"Insufficient wallet credits ({profile.credits:.2f} cr). "
            f"You tried to deposit {amount:.2f} cr."
        )

    profile.credits -= amount
    account.balance += amount
    _touch(account)
    _record_transaction(
        db,
        account_id=account.client_id,
        transaction_type=BankTransactionType.DEPOSIT,
        amount=amount,
        memo=f"Wallet to {account.account_number}",
    )
    db.commit()
    db.refresh(account)
    db.refresh(profile)
    return {
        "account": account_summary(db, client_id),
        "game_result": _game_result(profile, f"Deposited {amount:.2f} cr to {account.account_number}."),
    }


def withdraw(db: Session, client_id: str, amount: float) -> dict[str, Any]:
    if amount < MIN_AMOUNT:
        raise ValueError("Withdrawal amount must be at least 0.01 credits")

    profile = get_or_create_profile(db, client_id)
    account = get_or_create_bank_account(db, client_id)
    if account.balance < amount:
        raise ValueError(
            f"Insufficient bank balance ({account.balance:.2f} cr). "
            f"You tried to withdraw {amount:.2f} cr."
        )

    account.balance -= amount
    profile.credits += amount
    _touch(account)
    _record_transaction(
        db,
        account_id=account.client_id,
        transaction_type=BankTransactionType.WITHDRAW,
        amount=amount,
        memo=f"{account.account_number} to wallet",
    )
    db.commit()
    db.refresh(account)
    db.refresh(profile)
    return {
        "account": account_summary(db, client_id),
        "game_result": _game_result(profile, f"Withdrew {amount:.2f} cr to your wallet."),
    }


def _resolve_recipient(db: Session, *, email: str | None, account_number: str | None) -> BankAccount:
    if email:
        client = db.query(Client).filter(Client.email == email.lower().strip()).first()
        if not client:
            raise ValueError(f"No account holder found for email '{email}'")
        return get_or_create_bank_account(db, client.id)

    if account_number:
        account = (
            db.query(BankAccount)
            .filter(BankAccount.account_number == account_number.upper().strip())
            .first()
        )
        if not account:
            raise ValueError(f"Bank account '{account_number}' not found")
        return account

    raise ValueError("Tell me who to pay, e.g. transfer 100 to trader@starfall.corp")


def transfer(
    db: Session,
    client_id: str,
    amount: float,
    *,
    recipient_email: str | None = None,
    recipient_account: str | None = None,
    memo: str = "",
) -> dict[str, Any]:
    if amount < MIN_AMOUNT:
        raise ValueError("Transfer amount must be at least 0.01 credits")

    sender = get_or_create_bank_account(db, client_id)
    recipient = _resolve_recipient(db, email=recipient_email, account_number=recipient_account)
    if recipient.client_id == sender.client_id:
        raise ValueError("You cannot transfer funds to your own account")

    if sender.balance < amount:
        raise ValueError(
            f"Insufficient bank balance ({sender.balance:.2f} cr). "
            f"You tried to transfer {amount:.2f} cr."
        )

    sender.balance -= amount
    recipient.balance += amount
    _touch(sender)
    _touch(recipient)

    recipient_client = db.get(Client, recipient.client_id)
    sender_client = db.get(Client, client_id)
    note = memo or f"Transfer to {recipient.account_number}"

    _record_transaction(
        db,
        account_id=sender.client_id,
        transaction_type=BankTransactionType.TRANSFER_OUT,
        amount=amount,
        counterparty_client_id=recipient.client_id,
        counterparty_account=recipient.account_number,
        memo=note,
    )
    _record_transaction(
        db,
        account_id=recipient.client_id,
        transaction_type=BankTransactionType.TRANSFER_IN,
        amount=amount,
        counterparty_client_id=sender.client_id,
        counterparty_account=sender.account_number,
        memo=f"From {sender.account_number}" + (f": {memo}" if memo else ""),
    )
    db.commit()
    db.refresh(sender)

    profile = get_or_create_profile(db, client_id)
    recipient_label = recipient_client.display_name if recipient_client else recipient.account_number
    return {
        "account": account_summary(db, client_id),
        "recipient": recipient.account_number,
        "game_result": _game_result(
            profile,
            f"Transferred {amount:.2f} cr to {recipient_label} ({recipient.account_number}).",
        ),
    }


def _extract_amount(text: str, payload: dict[str, Any]) -> float | None:
    if payload.get("amount") is not None:
        return float(payload["amount"])
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:cr|credits?)?", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _extract_recipient(text: str, payload: dict[str, Any]) -> tuple[str | None, str | None]:
    email = payload.get("recipient_email") or payload.get("email")
    account = payload.get("recipient_account") or payload.get("account_number")
    if email:
        return str(email), None
    if account:
        return None, str(account).upper()

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    if email_match:
        return email_match.group(0), None

    acct_match = re.search(r"(sf[-\w]+)", text, re.IGNORECASE)
    if acct_match:
        return None, acct_match.group(1).upper()

    to_match = re.search(r"\bto\s+([\w.+-@]+)", text, re.IGNORECASE)
    if to_match:
        token = to_match.group(1)
        if "@" in token:
            return token, None
        if token.upper().startswith("SF-"):
            return None, token.upper()
    return None, None


def parse_banking_action(instruction: str, payload: dict[str, Any]) -> str:
    if payload.get("action"):
        return str(payload["action"]).lower()

    text = instruction.lower().strip()
    if any(word in text for word in ("help", "commands", "what can you")):
        return "help"
    if any(phrase in text for phrase in ("balance", "account status", "my account", "how much")):
        return "balance"
    if any(phrase in text for phrase in ("history", "transactions", "statement", "recent")):
        return "history"
    if "deposit" in text:
        return "deposit"
    if "withdraw" in text or "withdrawal" in text:
        return "withdraw"
    if "transfer" in text or "send" in text or "pay" in text:
        return "transfer"
    return "help"


def format_balance_message(summary: dict[str, Any]) -> str:
    return (
        f"{BANK_NAME}\n"
        f"Account: {summary['account_number']} ({summary['holder_name']})\n"
        f"Bank balance: {summary['bank_balance']} cr\n"
        f"Wallet credits: {summary['wallet_credits']} cr\n"
        f"Total liquid: {summary['total_liquid']} cr"
    )


def format_history_message(transactions: list[dict[str, Any]]) -> str:
    if not transactions:
        return "No transactions on this account yet."
    lines = ["Recent transactions:"]
    for tx in transactions:
        direction = tx["type"].replace("_", " ")
        cp = f" -> {tx['counterparty_account']}" if tx.get("counterparty_account") else ""
        lines.append(f"- {direction}: {tx['amount']} cr{cp} ({tx.get('memo') or '—'})")
    return "\n".join(lines)


def banker_respond(
    db: Session,
    client_id: str | None,
    instruction: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    action = parse_banking_action(instruction, payload)

    if action == "help":
        return {
            "message": (
                f"I am your {BANK_NAME} banker. Each trader has an account (SF-…).\n"
                "Wallet credits are cash on hand; bank balance is secured at the branch.\n\n"
                "Commands:\n"
                "- balance — account and wallet summary\n"
                "- deposit 500 — move wallet credits into your bank account\n"
                "- withdraw 200 — move bank funds to your wallet\n"
                "- transfer 100 to trader@starfall.corp — pay another trader\n"
                "- transfer 50 to SF-ABC123 — pay by account number\n"
                "- history — recent transactions"
            ),
            "action": action,
            "suggestions": ["balance", "deposit 500", "withdraw 200", "transfer 100 to admin@starfall.corp"],
        }

    if not client_id:
        return {
            "message": "Sign in via Marketplace to open your galactic bank account.",
            "action": action,
            "suggestions": ["Sign in, then ask: balance"],
        }

    if action == "balance":
        summary = account_summary(db, client_id)
        return {
            "message": format_balance_message(summary),
            "action": action,
            "data": {"account": summary},
            "suggestions": ["deposit 500", "history", "transfer 100 to trader@starfall.corp"],
        }

    if action == "history":
        summary = account_summary(db, client_id)
        transactions = list_recent_transactions(db, client_id)
        return {
            "message": format_balance_message(summary) + "\n\n" + format_history_message(transactions),
            "action": action,
            "data": {"account": summary, "transactions": transactions},
            "suggestions": ["balance", "deposit 500"],
        }

    amount = _extract_amount(instruction, payload)
    if action in ("deposit", "withdraw", "transfer") and amount is None:
        return {
            "message": f"How many credits should I {action}? e.g. {action} 500",
            "action": action,
            "suggestions": [f"{action} 500", "balance"],
        }

    try:
        if action == "deposit":
            result = deposit(db, client_id, amount)
            summary = result["account"]
            return {
                "message": (
                    f"Deposited {amount:.2f} cr.\n"
                    + format_balance_message(summary)
                ),
                "action": action,
                "data": result,
                "game_result": result.get("game_result"),
                "suggestions": ["balance", "history"],
            }

        if action == "withdraw":
            result = withdraw(db, client_id, amount)
            summary = result["account"]
            return {
                "message": (
                    f"Withdrew {amount:.2f} cr to your wallet.\n"
                    + format_balance_message(summary)
                ),
                "action": action,
                "data": result,
                "game_result": result.get("game_result"),
                "suggestions": ["balance", "history"],
            }

        if action == "transfer":
            email, account = _extract_recipient(instruction, payload)
            memo = str(payload.get("memo") or "")
            if " for " in instruction.lower():
                memo = instruction.split(" for ", 1)[-1].strip()
            result = transfer(
                db,
                client_id,
                amount,
                recipient_email=email,
                recipient_account=account,
                memo=memo,
            )
            summary = result["account"]
            return {
                "message": (
                    f"Transfer complete.\n"
                    + format_balance_message(summary)
                ),
                "action": action,
                "data": result,
                "game_result": result.get("game_result"),
                "suggestions": ["balance", "history"],
            }
    except ValueError as exc:
        return {
            "message": str(exc),
            "action": action,
            "suggestions": ["balance", "help"],
        }

    return banker_respond(db, client_id, "help", payload)

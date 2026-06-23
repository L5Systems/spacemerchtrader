/**
 * Shared game-layer types for the demo client.
 * @module
 */

/**
 * @typedef {'success' | 'warning' | 'info' | 'danger'} FeedbackVariant
 */

/**
 * @typedef {Object} GameResultFeedback
 * @property {string} title
 * @property {string} message
 * @property {string} [detail]
 * @property {FeedbackVariant} variant
 */

/**
 * @typedef {Object} GameWorld
 * @property {number} market_cycle
 * @property {number} online_players
 * @property {string} [event_message]
 */

/**
 * @typedef {Object} LeaderboardRow
 * @property {number} rank
 * @property {string} display_name
 * @property {number} level
 * @property {number} reputation
 * @property {number} credits
 */

/**
 * @typedef {Object} GameMission
 * @property {string} id
 * @property {string} title
 * @property {string} description
 * @property {boolean} completed
 * @property {number} progress
 * @property {number} target_quantity
 * @property {number} reward_credits
 * @property {number} reward_xp
 */

/**
 * @typedef {Object} PlayerStats
 * @property {string} display_name
 * @property {number} credits
 * @property {number} level
 * @property {number} xp
 * @property {number} reputation
 * @property {number} orders_completed
 * @property {number} xp_to_next_level
 */

/**
 * @typedef {Object} PlayerStatus
 * @property {PlayerStats} player
 * @property {GameMission[]} missions
 */

/**
 * @typedef {Object} GameMissionReward
 * @property {string} title
 */

/**
 * @typedef {Object} GameRewardResult
 * @property {number} [credits_earned]
 * @property {number} [xp_gained]
 * @property {number} [reputation_gained]
 * @property {number} [pickup_fee]
 * @property {number} [total_credits]
 * @property {string} [outcome]
 * @property {string} [outcome_detail]
 * @property {GameMissionReward[]} [mission_rewards]
 */

export {};

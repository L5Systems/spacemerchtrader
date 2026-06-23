export type FeedbackVariant = 'success' | 'warning' | 'info' | 'danger';

export interface GameResultFeedback {
  title: string;
  message: string;
  detail?: string;
  variant: FeedbackVariant;
}

export interface GameWorld {
  market_cycle: number;
  online_players: number;
  event_message?: string;
}

export interface LeaderboardRow {
  rank: number;
  display_name: string;
  level: number;
  reputation: number;
  credits: number;
}

export interface GameMission {
  id?: string;
  title: string;
  description: string;
  completed: boolean;
  progress: number;
  target_quantity: number;
  reward_credits: number;
  reward_xp: number;
}

export interface PlayerStats {
  display_name: string;
  credits: number;
  level: number;
  xp: number;
  reputation: number;
  orders_completed: number;
  xp_to_next_level: number;
}

export interface PlayerStatus {
  player: PlayerStats;
  missions: GameMission[];
}

export interface GameRewardResult {
  credits_earned?: number;
  xp_gained?: number;
  reputation_gained?: number;
  pickup_fee?: number;
  outcome?: string;
  outcome_detail?: string;
  total_credits?: number;
  mission_rewards?: Array<{ title: string }>;
}

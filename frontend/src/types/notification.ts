export interface Notification {
  id: number;
  type: "digest" | "staleness" | "pattern";
  content: string;
  read: boolean;
  read_at?: string;
  suppressed_by?: string;
  completed: boolean;
  completed_at?: string;
  created_at: string;
}

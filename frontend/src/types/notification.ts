export interface Notification {
  id: number;
  type: "digest" | "staleness" | "pattern";
  content: string;
  read: boolean;
  read_at?: string;
  suppressed_by?: string;
  created_at: string;
}

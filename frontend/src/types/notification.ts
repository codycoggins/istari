export interface Notification {
  id: number;
  type: "digest" | "staleness" | "pattern";
  content: string;
  read: boolean;
  readAt?: string;
  createdAt: string;
}

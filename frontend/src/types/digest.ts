export interface Digest {
  id: number;
  source: string;
  content_summary: string;
  items_json: Record<string, unknown> | null;
  reviewed: boolean;
  reviewed_at?: string;
  created_at: string;
}

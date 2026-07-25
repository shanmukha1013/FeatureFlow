export interface UserProfile {
  id: string;
  username: string;
  email: string;
  status: string;
  role: string | null;
  permissions: string[];
  mfa_enabled: boolean;
  created_at: string;
  last_login: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

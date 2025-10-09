
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

// This interface should be comprehensive, matching the backend model
export interface Obligation {
  id: string;
  contract_id: string;
  obligation_id: string;
  party: string;
  obligation_type: string;
  description: string;
  deadline: string | null;
  frequency: string | null;
  penalty_amount: number | null;
  rebate_amount: number | null;
  penalty_currency: string | null;
  rebate_currency: string | null;
  condition: string | null;
  trigger_conditions: string | null;
  status: string;
  risk_level: string;
  last_checked: string | null;
  next_check: string | null;
  compliance_status: string;
  compliance_evidence: string | null;
  breach_count: number;
  last_breach_date: string | null;
  created_at: string;
  updated_at: string;
  // We might want to fetch contract title for display, but it's not directly in Obligation model
  // For now, we'll rely on contract_id
}

export interface ObligationFilters {
  status?: string;
  obligation_type?: string;
  party?: string;
  risk_level?: string;
  contract_id?: string;
}

export const getObligations = async (filters: ObligationFilters = {}): Promise<Obligation[]> => {
  try {
    // Remove empty filters before sending
    const cleanFilters = Object.fromEntries(
      Object.entries(filters).filter(([_, v]) => v !== '' && v !== null)
    );

    const response = await axios.get(`${API_URL}/obligations/`, { params: cleanFilters });
    return response.data.obligations;
  } catch (error) {
    console.error("Error fetching obligations:", error);
    return [];
  }
};

export interface ObligationSummary {
  total_obligations: number;
  overdue_obligations: number;
  status_distribution: { [key: string]: number };
  type_distribution: { [key: string]: number };
  risk_distribution: { [key: string]: number };
  party_distribution: { [key: string]: number };
  compliance_distribution: { [key: string]: number };
}

export const getObligationsSummary = async (): Promise<ObligationSummary | null> => {
  try {
    const response = await axios.get(`${API_URL}/obligations/stats/summary`);
    return response.data;
  } catch (error) {
    console.error("Error fetching obligation summary:", error);
    return null;
  }
};

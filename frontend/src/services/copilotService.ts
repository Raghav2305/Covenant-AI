
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1/copilot';

export interface CopilotResponse {
  answer: string;
  sources: any[]; // Define a more specific type for sources later
}

export const askCopilot = async (query: string, contractId?: string): Promise<CopilotResponse> => {
  const payload: { query: string; contract_id?: string } = { query };
  if (contractId) {
    payload.contract_id = contractId;
  }
  const response = await axios.post(`${API_URL}/query`, payload);
  return response.data;
};

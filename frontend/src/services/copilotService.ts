
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1/copilot';

export interface CopilotResponse {
  answer: string;
  sources: any[]; // Define a more specific type for sources later
}

export const askCopilot = async (query: string): Promise<CopilotResponse> => {
  const response = await axios.post(`${API_URL}/query`, { query });
  return response.data;
};

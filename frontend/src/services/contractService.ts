
import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1'; // Assuming the backend runs on port 8000

// Define the structure of a Contract object based on the API
export type Contract = {
  id: string;
  title: string;
  party_a: string;
  party_b: string;
  contract_type: string;
  start_date: string;
  end_date: string;
  processing_status: string;
  created_at: string;
}

export const getContracts = async (): Promise<Contract[]> => {
  try {
    const response = await axios.get(`${API_URL}/contracts/`);
    // The actual list is nested in the response
    return response.data.contracts;
  } catch (error) {
    console.error("Error fetching contracts:", error);
    return [];
  }
};

export const uploadContract = async (formData: FormData): Promise<any> => {
  try {
    const response = await axios.post(`${API_URL}/contracts/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    console.error("Error uploading contract:", error);
    throw error;
  }
};

export const getContractById = async (id: string): Promise<any> => {
  try {
    const response = await axios.get(`${API_URL}/contracts/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching contract with id ${id}:`, error);
    throw error;
  }
};

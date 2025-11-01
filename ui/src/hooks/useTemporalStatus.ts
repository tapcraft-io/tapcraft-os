import { useQuery } from '@tanstack/react-query';
import client from './useApi';

interface HealthResponse {
  status: string;
  temporal: {
    connected: boolean;
    namespace: string;
  };
}

export function useTemporalStatus() {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await client.get('/health');
      return data;
    },
    staleTime: 30_000
  });
}

import { useQuery } from '@tanstack/react-query';
import client from './useApi';
import { Capability } from '../types';

export function useCapabilities() {
  return useQuery<Capability[]>({
    queryKey: ['capabilities'],
    queryFn: async () => {
      const { data } = await client.get('/config/capabilities');
      return data.capabilities ?? data;
    },
    staleTime: 60_000
  });
}

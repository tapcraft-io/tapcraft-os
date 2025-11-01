import { create } from 'zustand';

type Cable = {
  id: string;
  from: string;
  to: string;
  param: string;
};

type ModulePosition = {
  id: string;
  x: number;
  y: number;
};

type PatchBayState = {
  modulePositions: Record<string, ModulePosition>;
  cables: Cable[];
  setPosition: (id: string, x: number, y: number) => void;
  addCable: (cable: Cable) => void;
  removeCable: (id: string) => void;
  clear: () => void;
};

export const usePatchBayState = create<PatchBayState>((set) => ({
  modulePositions: {},
  cables: [],
  setPosition: (id, x, y) =>
    set((state) => ({
      modulePositions: {
        ...state.modulePositions,
        [id]: { id, x, y }
      }
    })),
  addCable: (cable) =>
    set((state) => ({
      cables: state.cables.some((c) => c.id === cable.id)
        ? state.cables
        : [...state.cables, cable]
    })),
  removeCable: (id) =>
    set((state) => ({
      cables: state.cables.filter((c) => c.id !== id)
    })),
  clear: () => set({ modulePositions: {}, cables: [] })
}));

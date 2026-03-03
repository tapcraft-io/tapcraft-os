# UI Restyle Design

## Goal
Replace the old "rebel control" theme with the warm zinc-based palette from UI sketches, and rewrite all 6 pages to match the sketch aesthetic while preserving backend API integration.

## Theme Tokens

From `ui_sketches/tapcraft_home_dashboard/code.html`:

| Token | Value | Usage |
|-------|-------|-------|
| `primary` | #ee8c2b | Orange accent, buttons, active states |
| `background-dark` | #111111 | Main background |
| `surface-dark` | #18181b | Sidebar, card backgrounds (zinc-900) |
| `surface-light` | #27272a | Elevated surfaces (zinc-800) |
| `border-dark` | #3f3f46 | Borders (zinc-700) |

**Font:** Inter (already in config, keep it)
**Icons:** Material Symbols Outlined (replace Heroicons)

## Files to Modify

### 1. Tailwind Config (`tailwind.config.cjs`)
- Remove: `holo`, `deck` color tokens
- Add: `primary`, `background-dark`, `surface-dark`, `surface-light`, `border-dark`
- Remove: `glass-panel` related shadows

### 2. Global CSS (`src/styles.css`)
- Remove: `.glass-panel`, `.holo-text`, `.holo-outline`
- Update: body background to `bg-background-dark`

### 3. Index HTML
- Add Material Symbols font link

### 4. AppShell (`src/pages/AppShell.tsx`)
- New sidebar with Material Symbols icons
- Navigation matching sketch style
- "New Workflow" CTA button
- Remove Heroicons import

### 5. Dashboard (`src/pages/Dashboard.tsx`)
- Rewrite to match `tapcraft_home_dashboard` sketch
- Keep: health + runs API queries
- Add: Status cards grid, Upcoming Schedules, Recent Activity table

### 6. Apps (`src/pages/Apps.tsx`)
- Restyle with new theme
- Keep: `useApps()` hook
- Update: card/list styling

### 7. Workflows (`src/pages/Workflows.tsx`)
- Restyle PatchBay + Inspector
- Keep: workflow + runs queries

### 8. Agent (`src/pages/Agent.tsx`)
- Restyle form with new theme
- Keep: `useCreateWorkflow()`, `useApps()` hooks

### 9. Runs (`src/pages/Runs.tsx`)
- Restyle table matching sketch aesthetic
- Keep: `useRuns()` hook

### 10. Settings (`src/pages/Settings.tsx`)
- Restyle ConfigPanel
- Keep: config query

## Implementation Order

1. Theme foundation (tailwind config, global CSS, fonts)
2. AppShell (sidebar/navigation)
3. Dashboard (entry point)
4. Apps, Workflows, Agent, Runs, Settings (remaining pages)

## Data Hooks Preserved

- `useApps(workspaceId)` - fetch apps list
- `useRuns(workspaceId)` - fetch runs list
- `useCreateWorkflow(workspaceId)` - create workflow mutation
- `useQuery` for health, config, workflows

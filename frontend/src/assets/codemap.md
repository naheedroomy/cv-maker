# frontend/src/assets/

## Responsibility

Shared CSS styles imported by multiple components. Currently a single module providing consistent styling for pill-group selectors.

## Design

### `selector.css` — Shared Selector Styles

Provides the visual foundation for selector components:
- `ModelSelector.vue`
- `CreativitySlider.vue`

**CSS classes provided**:

| Class | Purpose |
|---|---|
| `.pill-group` | Flex container with border, padding, rounded corners. White background with #e2e8f0 border |
| `.pill-option` | Individual pill button (32px height). Transparent background, transitions to blue when active |
| `.pill-option--active` | Active state: #2563eb blue background, white text |
| `.pill-option--disabled` | Disabled state: gray text, `cursor: not-allowed` |
| `.field-label` | Block-level label (14px, semibold) with 6px bottom margin |
| `.field-hint` | Descriptive hint text (12px, gray) below the selector |
| `.field-hint--warning` | Red variation for warning/alert hint text |

**Interaction**: Pill hover shows light gray background unless active or disabled. All transitions are 150ms ease.

## Integration Points

- **`ModelSelector.vue`**: Imports via `import '@/assets/selector.css'`
- **`CreativitySlider.vue`**: Imports via `import '@/assets/selector.css'`
- Each component adds its own scoped styles for component-specific layout (e.g., margin-bottom on the selector wrapper)

## Data & Control Flow

No data flow — this is purely presentational CSS. Components apply classes based on their internal model/value state. No JavaScript logic in this file.

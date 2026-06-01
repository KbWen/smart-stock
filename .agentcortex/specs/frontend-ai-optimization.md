---
status: frozen
module: frontend-ai
version: 1.0.0
---

# Frontend UI/Performance Optimization & AI Correctness Verification

Details the frontend layout and scroll performance enhancements, and verifies the correctness of the AI training pipeline.

## Acceptance Criteria

### AC1: SVG Sparkline Performance Optimization
- Rewrite `frontend/v4/src/components/charts/SparklineChart.tsx` to use pure React SVG rendering instead of Recharts.
- Remove `LineChart`, `Line`, and `ResponsiveContainer` imports from Recharts.
- Implement responsive SVG rendering using `viewBox="0 0 100 24"`, `width="100%"`, `height="24px"`, and `preserveAspectRatio="none"`.
- This eliminates JS-based `ResizeObserver` listener overhead and DOM reflow cost during list scrolling, optimizing scroll speed to 60 FPS.

### AC2: Visual Sparkline Gradient Area Chart
- In `SparklineChart.tsx`, render the sparkline as a gradient Area Chart.
- Create a `<linearGradient>` in the SVG:
  - If `changePercent >= 0` (gain), gradient transitions from `rgba(239, 68, 68, 0.2)` (red) to transparent.
  - If `changePercent < 0` (loss), gradient transitions from `rgba(34, 197, 94, 0.2)` (green) to transparent.
- Render the line path with a stroke of `strokeWidth={1.5}` and color matching the trend.
- Render the area path filled with the gradient, bounded at the bottom by `y = 24`.

### AC3: Dashboard Visual Enhancements & Micro-animations
- Add hover scale and borders in `CandidateRow.tsx`:
  - Enhance row background transition to include a subtle translate-x offset on hover.
  - Add active shadow effect for `isSelected` rows.
- Upgrade dashboard card classes in `Dashboard.tsx` to include glassmorphism filters (`backdrop-blur-xl`, `bg-white/5`, etc.) with transition classes.

### AC4: AI Training Correctness Verification
- Validate the AI training pipeline (`core/ai/trainer.py`) against:
  - Chronological splits (no look-ahead leakage).
  - Target labeling verification (20 trading days win/loss window).
  - Warm-up indicator calculations (proper NaN drop handling).
- Output an evaluation report on training logic correctness.

## Non-goals
- Modifying backend ML algorithms or retraining the default model with new architectures.
- Changing technical indicator math in `core/analysis.py`.

# Code Style Guide

To maintain a high-quality codebase, please adhere to the following style guidelines.

## Python (Backend & Core)

* **Standard**: Follow [PEP 8](https://peps.python.org/pep-0008/).
* **Formatter**: Use `black` or `autopep8` if available.
* **Imports**:

    ```python
    import os
    import sys
    # Third-party
    import pandas as pd
    import numpy as np
    # Local
    from core.data import load_from_db
    ```

* **Type Hinting**: Strongly encouraged for function signatures.

    ```python
    def calculate_sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
        ...
    ```

* **Docstrings**: Use Google-style docstrings for complex functions.

    ```python
    def predict_prob(df):
        """
        Calculates the probability of a price rise.

        Args:
            df (pd.DataFrame): Input market data.

        Returns:
            dict: {'prob': 0.85, 'version': 'v4.1'}
        """
    ```

## TypeScript / React (Frontend)

* **Standard**: Functional Components with Hooks.
* **Wrapper**: Use `React.FC` type for components.

    ```tsx
    interface Props {
        ticker: string;
    }
    const StockCard: React.FC<Props> = ({ ticker }) => { ... }
    ```

* **Styling**: Use **Tailwind CSS** utility classes. Avoid custom CSS files unless necessary for complex animations.
  * *Bad*: `style={{ marginTop: '10px' }}`
  * *Good*: `className="mt-2"`
* **Layout Safety (Tables/Virtualized Lists)**:
  * Keep row heights stable when using virtualization.
  * For long text or dynamic tags, prefer `truncate`, `min-w-0`, and summary badges (e.g., `+N`) to avoid layout breakage.
  * Avoid unbounded wrapping content inside fixed-height rows.
* **Accessibility**:
  * Add `title` on truncated financial labels when useful for hover inspection.
* **State Management**: Use local `useState` for simple UI state. Lift state up only when necessary.
* **Naming**:
  * Components: `PascalCase` (e.g., `StockList.tsx`)
  * Functions/Variables: `camelCase` (e.g., `fetchData`)
  * Interfaces: `PascalCase` (e.g., `StockData`)

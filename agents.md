## Core Rules

* Keep functions small and single-purpose.
* Prefer modular architecture over large files.
* Use meaningful file and folder names.
* Minimize unnecessary whitespace and verbosity to preserve tokens.
* Add only essential comments.
* Write reusable and maintainable code.
* Avoid duplicate logic.
* Prefer configuration over hardcoding.


---
## Requirements

### Python

```txt
requirements.txt
```

Install:

```bash
pip install -r requirements.txt
```

### Node.js

```txt
package.json
package-lock.json
```

Rules:

* Commit lock files
* Use lightweight packages
* Remove unused deps
## Coding Standards

### Functions

* One responsibility per function.
* Target 5-20 lines when possible.
* Avoid deep nesting.
* Return early.
* Use helper functions for repeated logic.

Example:

```python
def validate_email(email:str)->bool:
    return "@" in email and "." in email
```

---

### Modular Design

* Split logic into modules.
* Keep business logic separate from API/UI.
* Use utility files for shared helpers.
* Keep configuration centralized.


---

## Environment Setup

### Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Node.js

```bash
npm install
cp .env.example .env
npm run dev
```

---

## Comments

* Write comments only when logic is non-obvious.
* Avoid redundant comments.
* Prefer self-explanatory naming.

Good:

```python
# Retry because external API fails intermittently
```

Bad:

```python
# Increment i
i+=1
```

---

## Naming Rules

### Files

* snake_case for Python.
* kebab-case for frontend files.
* Clear and descriptive names.

Good:

```txt
user_service.py
payment-handler.ts
```

Bad:

```txt
final.py
newcode.ts
```

---

## Error Handling

```python
def parse_data(data:dict):
    if not data:
        raise ValueError("empty data")
    return data.get("id")
```

* Fail fast.
* Use specific exceptions.
* Never silently ignore errors.

---

## Token Optimization

* Avoid unnecessary explanations in code.
* Keep prompts concise.
* Remove dead code.
* Prefer compact implementations when readability is maintained.

Compact Example:

```python
nums=[x*x for x in arr if x>0]
```

---

## Configuration

### .env Example

```env
APP_ENV=dev
DB_URL=postgres://user:pass@localhost/db
API_KEY=your_key
```

### Access Config Safely

```python
from os import getenv
API_KEY=getenv("API_KEY")
```

---

## Testing

```bash
pytest
npm test
```

Rules:

* Test core logic.
* Keep tests isolated.
* Mock external services.

---

## Git Rules

```bash
git checkout -b feature/auth
```

Commit format:

```txt
feat: add auth middleware
fix: resolve token refresh bug
refactor: split user service
```

---

## Performance

* Avoid unnecessary loops.
* Cache expensive operations.
* Lazy load when possible.
* Optimize DB/API calls.

---

## Security

* Never hardcode secrets.
* Validate all inputs.
* Sanitize user data.
* Use environment variables.

---

## Final Development Checklist

* Small functions
* Modular structure
* Clean naming
* Essential comments only
* Environment configured
* No dead code
* Proper error handling
* Tests added
* Token-efficient implementation

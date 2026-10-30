# FindChain

Privacy-first lost and found application foundation using React/Vite, Flask, SQLite and a Solidity contract. Items, claims and handover workflow persist in SQLite. Personal claim text stays out of public item APIs. Blockchain-related actions are marked `local_demo`; this backend does not currently submit transactions.

## Run locally

Requirements: Python 3.10+, Node 20+, npm. In separate terminals:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY='replace-with-a-long-random-secret'
python app.py
```

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API defaults to http://localhost:5000/api (override with `VITE_API_URL`). SQLite creates `backend/findchain.db` automatically.

## Demo accounts

- User: `demo@findchain.local` / `FindChain123!`
- Admin: `admin@findchain.local` / `Admin123!`

Change these demo passwords before sharing a deployed instance. Set a strong `SECRET_KEY` in the environment.

## Blockchain

`blockchain/` contains the Hardhat contract and tests. From that directory run `npm install`, `npx hardhat node`, then deploy with `npx hardhat run scripts/deploy.js --network localhost`. The backend does not yet call the deployed contract, and the interface does not yet connect MetaMask. API events therefore remain `local_demo`; no transaction hashes are fabricated.

## Implemented

- Registration/login with hashed passwords, JWT protected routes and admin authorization.
- Lost/found reporting, generated IDs, SHA-256 record fingerprints, search and filters.
- Private-by-default identifying details; public listings omit that field.
- Ownership claims, administrator review, claimant notification and two-party handover confirmation.
- Dashboard and counts from SQLite, admin overview, and transaction history with honest local-demo labels.
- Responsive dark interface, account profile, item detail, search and category/status filter.

## Tests and known scope

Run backend tests with `python -m unittest discover -s tests -v` from `backend/`; run contract tests with `cd blockchain; npm install; npx hardhat test`. Test execution here was blocked because required Python packages were not installed and this environment could not reach PyPI. Evidence file upload, email delivery, CSV export, advanced matching, suspend-user tooling, browser wallet integration, and backend-to-contract signing are not implemented yet. The React app and contract are a functional demo foundation, not a completed production blockchain integration.

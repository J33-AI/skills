"""Generate the fixture repositories the eval suite runs against.

Small, deterministic, purpose-built repos — each one exists to exercise a
specific documentation problem. They are generated rather than committed so the
suite stays readable: nine repos as one file of literals, not four hundred files
in version control.

    python make_fixtures.py              # write all fixtures
    python make_fixtures.py --list       # names and what each one tests
    python make_fixtures.py --only monorepo
    python make_fixtures.py --clean

Each fixture is deliberately *small enough to read in full* — a documenter that
cannot get these right will not get a real codebase right either, and when an
assertion fails you can see why in thirty seconds.
"""

from __future__ import annotations

import argparse
import os
import shutil
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")


def d(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


# ═══════════════════════════════════════════════════════════════════════════
# 1. backend-only — FastAPI + SQLAlchemy + Alembic. Has a real schema with
#    constraints that encode business rules, and cascades that differ.
# ═══════════════════════════════════════════════════════════════════════════
BACKEND_ONLY = {
    "README.md": d("""
        # Loanbook API

        Internal service for tracking small business loan applications.
        FastAPI + SQLAlchemy + Alembic. No frontend — consumed by the
        back-office React app in a separate repository.
    """),
    "requirements.txt": "fastapi\nsqlalchemy\nalembic\npydantic\npsycopg2-binary\n",
    "alembic.ini": "[alembic]\nscript_location = alembic\n",
    "app/main.py": d('''
        """Application entry point."""
        from fastapi import FastAPI

        from app.api.loans import router as loans_router
        from app.api.borrowers import router as borrowers_router

        app = FastAPI(title="Loanbook API", version="2.1.0")
        app.include_router(borrowers_router, prefix="/api/v1/borrowers")
        app.include_router(loans_router, prefix="/api/v1/loans")


        @app.get("/health")
        def health():
            return {"status": "ok"}
    '''),
    "app/models/base.py": d('''
        from datetime import datetime

        from sqlalchemy import DateTime, func
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


        class Base(DeclarativeBase):
            pass


        class TimestampMixin:
            created_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True), server_default=func.now(), nullable=False)
            updated_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True), server_default=func.now(),
                onupdate=func.now(), nullable=False)
    '''),
    "app/models/borrower.py": d('''
        """Borrower — the business applying for credit."""
        import uuid
        from enum import StrEnum

        from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
        from sqlalchemy.orm import Mapped, mapped_column, relationship

        from app.models.base import Base, TimestampMixin


        class BorrowerStatus(StrEnum):
            PROSPECT = "prospect"
            ACTIVE = "active"
            SUSPENDED = "suspended"
            CLOSED = "closed"


        class Borrower(TimestampMixin, Base):
            __tablename__ = "borrowers"
            __table_args__ = (
                CheckConstraint(
                    "status IN ('prospect','active','suspended','closed')",
                    name="ck_borrowers_status"),
                # A borrower may not owe more than their approved facility.
                CheckConstraint(
                    "outstanding_cents <= facility_limit_cents",
                    name="ck_borrowers_within_facility"),
            )

            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
            registration_number: Mapped[str] = mapped_column(
                String(20), unique=True, nullable=False)
            status: Mapped[str] = mapped_column(String(20), nullable=False,
                                                default="prospect")
            facility_limit_cents: Mapped[int] = mapped_column(nullable=False,
                                                              default=0)
            outstanding_cents: Mapped[int] = mapped_column(nullable=False,
                                                           default=0)
            # Deleting a borrower deliberately keeps their loans for audit.
            loans = relationship("Loan", back_populates="borrower",
                                 passive_deletes=True)
    '''),
    "app/models/loan.py": d('''
        """Loan and repayment schedule."""
        import uuid
        from datetime import date
        from enum import StrEnum

        from sqlalchemy import CheckConstraint, Date, ForeignKey, String
        from sqlalchemy.orm import Mapped, mapped_column, relationship

        from app.models.base import Base, TimestampMixin


        class LoanStatus(StrEnum):
            DRAFT = "draft"
            SUBMITTED = "submitted"
            APPROVED = "approved"
            DISBURSED = "disbursed"
            REPAID = "repaid"
            DEFAULTED = "defaulted"
            WITHDRAWN = "withdrawn"


        class Loan(TimestampMixin, Base):
            __tablename__ = "loans"
            __table_args__ = (
                CheckConstraint(
                    "status IN ('draft','submitted','approved','disbursed',"
                    "'repaid','defaulted','withdrawn')",
                    name="ck_loans_status"),
                CheckConstraint("principal_cents > 0",
                                name="ck_loans_principal_positive"),
                # Approval must record who approved it.
                CheckConstraint(
                    "(status <> 'approved') OR (approved_by IS NOT NULL)",
                    name="ck_loans_approval_attributed"),
            )

            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            reference: Mapped[str] = mapped_column(String(24), unique=True,
                                                   nullable=False)
            borrower_id: Mapped[uuid.UUID] = mapped_column(
                ForeignKey("borrowers.id", ondelete="RESTRICT"), nullable=False)
            status: Mapped[str] = mapped_column(String(20), nullable=False,
                                                default="draft")
            principal_cents: Mapped[int] = mapped_column(nullable=False)
            term_months: Mapped[int] = mapped_column(nullable=False)
            approved_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
            disbursed_on: Mapped[date | None] = mapped_column(Date, nullable=True)

            borrower = relationship("Borrower", back_populates="loans")
            repayments = relationship("Repayment", back_populates="loan",
                                      cascade="all, delete-orphan")


        class Repayment(TimestampMixin, Base):
            __tablename__ = "repayments"

            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            loan_id: Mapped[uuid.UUID] = mapped_column(
                ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
            due_on: Mapped[date] = mapped_column(Date, nullable=False)
            amount_cents: Mapped[int] = mapped_column(nullable=False)
            paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)

            loan = relationship("Loan", back_populates="repayments")
    '''),
    "app/api/loans.py": d('''
        """Loan endpoints."""
        import uuid

        from fastapi import APIRouter, Depends, HTTPException

        from app.services.loan_service import LoanService, get_loan_service

        router = APIRouter()


        @router.get("/")
        def list_loans(borrower_id: uuid.UUID | None = None,
                       status: str | None = None,
                       svc: LoanService = Depends(get_loan_service)):
            return svc.list_loans(borrower_id=borrower_id, status=status)


        @router.post("/")
        def create_loan(payload: dict,
                        svc: LoanService = Depends(get_loan_service)):
            return svc.create_draft(payload)


        @router.post("/{loan_id}/submit")
        def submit_loan(loan_id: uuid.UUID,
                        svc: LoanService = Depends(get_loan_service)):
            return svc.submit(loan_id)


        @router.post("/{loan_id}/approve")
        def approve_loan(loan_id: uuid.UUID, approver_id: uuid.UUID,
                         svc: LoanService = Depends(get_loan_service)):
            return svc.approve(loan_id, approver_id)


        @router.post("/{loan_id}/disburse")
        def disburse_loan(loan_id: uuid.UUID,
                          svc: LoanService = Depends(get_loan_service)):
            return svc.disburse(loan_id)
    '''),
    "app/api/borrowers.py": d('''
        """Borrower endpoints."""
        import uuid

        from fastapi import APIRouter

        router = APIRouter()


        @router.get("/")
        def list_borrowers(q: str | None = None):
            ...


        @router.post("/")
        def create_borrower(payload: dict):
            ...


        @router.get("/{borrower_id}")
        def get_borrower(borrower_id: uuid.UUID):
            ...
    '''),
    "app/services/loan_service.py": d('''
        """Loan lifecycle. All state changes go through here."""
        import uuid

        VALID_TRANSITIONS = {
            "draft": {"submitted", "withdrawn"},
            "submitted": {"approved", "withdrawn"},
            "approved": {"disbursed", "withdrawn"},
            "disbursed": {"repaid", "defaulted"},
            "repaid": set(),
            "defaulted": set(),
            "withdrawn": set(),
        }


        class LoanService:
            def __init__(self, db, ledger):
                self._db = db
                self._ledger = ledger

            def list_loans(self, borrower_id=None, status=None):
                ...

            def create_draft(self, payload):
                ...

            def submit(self, loan_id: uuid.UUID):
                """Draft -> submitted. Checks the borrower is active."""
                ...

            def approve(self, loan_id: uuid.UUID, approver_id: uuid.UUID):
                """Records the approver. The CHECK constraint enforces it too."""
                ...

            def disburse(self, loan_id: uuid.UUID):
                """Approved -> disbursed.

                Writes the loan row, builds the repayment schedule, and posts to
                the ledger. The ledger call is OUTSIDE the transaction, so a
                ledger failure leaves a disbursed loan with no ledger entry.
                """
                ...
        def get_loan_service():
            ...
    '''),
    "alembic/versions/0001_initial.py": d('''
        """initial schema"""
        revision = "0001"
        down_revision = None


        def upgrade():
            # borrowers, loans, repayments
            ...


        def downgrade():
            ...
    '''),
    "alembic/versions/0002_add_facility_check.py": d('''
        """add facility limit check

        NOTE: the model declares ck_borrowers_within_facility but this migration
        creates it as ck_borrower_facility — the names disagree.
        """
        revision = "0002"
        down_revision = "0001"


        def upgrade():
            ...
    '''),
}

# ═══════════════════════════════════════════════════════════════════════════
# 2. frontend-only — React + TypeScript, no server in the repo at all.
# ═══════════════════════════════════════════════════════════════════════════
FRONTEND_ONLY = {
    "README.md": d("""
        # Loanbook Console

        Back-office UI for the Loanbook API. React + TypeScript + Vite.
        The API lives in a separate repository.
    """),
    "package.json": d("""
        {
          "name": "loanbook-console",
          "type": "module",
          "scripts": {
            "dev": "vite",
            "build": "tsc && vite build",
            "test": "vitest"
          },
          "dependencies": {
            "react": "^18.3.0",
            "react-router-dom": "^6.26.0",
            "zustand": "^4.5.0",
            "axios": "^1.7.0",
            "@tanstack/react-query": "^5.51.0"
          }
        }
    """),
    "vite.config.ts": d("""
        import { defineConfig } from 'vite';
        import react from '@vitejs/plugin-react';

        export default defineConfig({ plugins: [react()] });
    """),
    "src/main.tsx": d("""
        import React from 'react';
        import ReactDOM from 'react-dom/client';
        import { RouterProvider } from 'react-router-dom';
        import { router } from './routes';

        ReactDOM.createRoot(document.getElementById('root')!).render(
          <React.StrictMode><RouterProvider router={router} /></React.StrictMode>
        );
    """),
    "src/routes.tsx": d("""
        import { createBrowserRouter } from 'react-router-dom';
        import LoanList from './features/loans/LoanList';
        import LoanDetail from './features/loans/LoanDetail';
        import BorrowerList from './features/borrowers/BorrowerList';
        import Login from './features/auth/Login';

        export const router = createBrowserRouter([
          { path: '/login', element: <Login /> },
          { path: '/loans', element: <LoanList /> },
          { path: '/loans/:id', element: <LoanDetail /> },
          { path: '/borrowers', element: <BorrowerList /> },
        ]);
    """),
    "src/lib/api.ts": d("""
        import axios from 'axios';

        export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL });

        // Attaches the bearer token. There is no refresh handling — a 401 is
        // surfaced to the caller and the user is bounced to /login.
        api.interceptors.request.use((config) => {
          const token = localStorage.getItem('token');
          if (token) config.headers.Authorization = `Bearer ${token}`;
          return config;
        });
    """),
    "src/store/loanStore.ts": d("""
        import { create } from 'zustand';

        interface LoanState {
          filters: { status?: string; borrowerId?: string };
          setFilter: (key: string, value: string) => void;
          reset: () => void;
        }

        export const useLoanStore = create<LoanState>((set) => ({
          filters: {},
          setFilter: (key, value) =>
            set((s) => ({ filters: { ...s.filters, [key]: value } })),
          reset: () => set({ filters: {} }),
        }));
    """),
    "src/features/loans/LoanList.tsx": d("""
        import { useQuery } from '@tanstack/react-query';
        import { api } from '../../lib/api';
        import { useLoanStore } from '../../store/loanStore';

        export default function LoanList() {
          const filters = useLoanStore((s) => s.filters);
          const { data, isLoading } = useQuery({
            queryKey: ['loans', filters],
            queryFn: () => api.get('/loans', { params: filters }).then(r => r.data),
          });
          if (isLoading) return <p>Loading…</p>;
          return <table>{/* rows */}</table>;
        }
    """),
    "src/features/loans/LoanDetail.tsx": d("""
        import { useParams } from 'react-router-dom';

        export default function LoanDetail() {
          const { id } = useParams();
          return <section>Loan {id}</section>;
        }
    """),
    "src/features/borrowers/BorrowerList.tsx": d("""
        export default function BorrowerList() {
          return <table>{/* borrowers */}</table>;
        }
    """),
    "src/features/auth/Login.tsx": d("""
        import { api } from '../../lib/api';

        export default function Login() {
          async function submit(email: string, password: string) {
            const { data } = await api.post('/auth/login', { email, password });
            localStorage.setItem('token', data.access_token);
          }
          return <form>{/* fields */}</form>;
        }
    """),
}

# ═══════════════════════════════════════════════════════════════════════════
# 3. no-database — a stateless transform service. Nothing is persisted.
# ═══════════════════════════════════════════════════════════════════════════
NO_DATABASE = {
    "README.md": d("""
        # Rateflow

        Stateless currency conversion service. Fetches rates from an upstream
        provider, caches them in memory for 60 seconds, converts amounts.

        **There is no database.** Nothing is persisted between restarts.
    """),
    "requirements.txt": "fastapi\nhttpx\npydantic\n",
    "app/main.py": d('''
        """Rateflow — stateless conversion API."""
        from fastapi import FastAPI, HTTPException

        from app.rates import RateCache
        from app.convert import convert_amount

        app = FastAPI(title="Rateflow")
        cache = RateCache(ttl_seconds=60)


        @app.get("/health")
        def health():
            return {"status": "ok", "cached_pairs": cache.size()}


        @app.get("/convert")
        async def convert(base: str, quote: str, amount: float):
            rate = await cache.get(base, quote)
            if rate is None:
                raise HTTPException(502, "upstream rate unavailable")
            return {"base": base, "quote": quote, "amount": amount,
                    "converted": convert_amount(amount, rate), "rate": rate}
    '''),
    "app/rates.py": d('''
        """In-memory rate cache. Deliberately not persisted."""
        import time

        import httpx

        UPSTREAM = "https://rates.example.com/v1/latest"


        class RateCache:
            def __init__(self, ttl_seconds: int = 60):
                self._ttl = ttl_seconds
                self._store: dict[tuple[str, str], tuple[float, float]] = {}

            def size(self) -> int:
                return len(self._store)

            async def get(self, base: str, quote: str) -> float | None:
                key = (base.upper(), quote.upper())
                hit = self._store.get(key)
                if hit and (time.time() - hit[1]) < self._ttl:
                    return hit[0]
                rate = await self._fetch(*key)
                if rate is not None:
                    self._store[key] = (rate, time.time())
                return rate

            async def _fetch(self, base: str, quote: str) -> float | None:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(UPSTREAM,
                                            params={"base": base, "symbols": quote})
                    if resp.status_code != 200:
                        return None
                    return resp.json()["rates"].get(quote)
    '''),
    "app/convert.py": d('''
        """Pure conversion arithmetic."""
        from decimal import ROUND_HALF_UP, Decimal


        def convert_amount(amount: float, rate: float) -> float:
            """Convert and round to 2dp, half-up.

            Floats are used throughout, which is wrong for money — see the note
            in the README backlog.
            """
            value = Decimal(str(amount)) * Decimal(str(rate))
            return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    '''),
}

# ═══════════════════════════════════════════════════════════════════════════
# 4. minimal-api — two endpoints, nothing else.
# ═══════════════════════════════════════════════════════════════════════════
MINIMAL_API = {
    "README.md": "# Pingbox\n\nA health probe target. Two endpoints.\n",
    "requirements.txt": "flask\n",
    "app.py": d('''
        """Pingbox — the smallest useful service."""
        import os
        import time

        from flask import Flask, jsonify

        app = Flask(__name__)
        STARTED = time.time()


        @app.get("/ping")
        def ping():
            return jsonify(pong=True)


        @app.get("/uptime")
        def uptime():
            return jsonify(seconds=round(time.time() - STARTED, 1),
                           version=os.environ.get("BUILD_SHA", "dev"))
    '''),
}

# ═══════════════════════════════════════════════════════════════════════════
# 5. monorepo — three packages, one shared, with a cross-package contract.
# ═══════════════════════════════════════════════════════════════════════════
MONOREPO = {
    "README.md": d("""
        # Shipyard

        Monorepo. `packages/shared` holds the types both sides import.

            packages/api      Express + Prisma
            packages/web      React
            packages/shared   types and validation
    """),
    "package.json": d("""
        {
          "name": "shipyard",
          "private": true,
          "workspaces": ["packages/*"]
        }
    """),
    "packages/shared/src/types.ts": d("""
        export type ShipmentStatus =
          | 'draft' | 'booked' | 'in_transit' | 'delivered' | 'cancelled';

        export interface Shipment {
          id: string;
          reference: string;
          status: ShipmentStatus;
          originPort: string;
          destinationPort: string;
          etaIso: string | null;
        }

        /** Both the API and the web app import this. Changing it breaks both. */
        export const TERMINAL_STATUSES: ShipmentStatus[] =
          ['delivered', 'cancelled'];
    """),
    "packages/shared/src/validate.ts": d("""
        import { ShipmentStatus, TERMINAL_STATUSES } from './types';

        export function canTransition(from: ShipmentStatus,
                                      to: ShipmentStatus): boolean {
          if (TERMINAL_STATUSES.includes(from)) return false;
          const allowed: Record<ShipmentStatus, ShipmentStatus[]> = {
            draft: ['booked', 'cancelled'],
            booked: ['in_transit', 'cancelled'],
            in_transit: ['delivered'],
            delivered: [],
            cancelled: [],
          };
          return allowed[from].includes(to);
        }
    """),
    "packages/api/prisma/schema.prisma": d("""
        datasource db { provider = "postgresql"  url = env("DATABASE_URL") }
        generator client { provider = "prisma-client-js" }

        model Shipment {
          id              String    @id @default(uuid())
          reference       String    @unique
          status          String    @default("draft")
          originPort      String
          destinationPort String
          etaIso          DateTime?
          events          Event[]
          createdAt       DateTime  @default(now())
        }

        model Event {
          id         String   @id @default(uuid())
          shipmentId String
          shipment   Shipment @relation(fields: [shipmentId], references: [id],
                                        onDelete: Cascade)
          kind       String
          payload    Json
          createdAt  DateTime @default(now())
        }
    """),
    "packages/api/src/server.ts": d("""
        import express from 'express';
        import { shipmentRouter } from './routes/shipments';

        const app = express();
        app.use(express.json());
        app.use('/api/shipments', shipmentRouter);
        app.listen(process.env.PORT ?? 3000);
    """),
    "packages/api/src/routes/shipments.ts": d("""
        import { Router } from 'express';
        import { canTransition } from '@shipyard/shared/src/validate';
        import { prisma } from '../db';

        export const shipmentRouter = Router();

        shipmentRouter.get('/', async (_req, res) => {
          res.json(await prisma.shipment.findMany());
        });

        shipmentRouter.post('/', async (req, res) => {
          res.status(201).json(await prisma.shipment.create({ data: req.body }));
        });

        shipmentRouter.post('/:id/status', async (req, res) => {
          const current = await prisma.shipment.findUniqueOrThrow({
            where: { id: req.params.id } });
          if (!canTransition(current.status as never, req.body.status)) {
            return res.status(409).json({ error: 'INVALID_TRANSITION' });
          }
          res.json(await prisma.shipment.update({
            where: { id: req.params.id }, data: { status: req.body.status } }));
        });
    """),
    "packages/api/src/db.ts": "import { PrismaClient } from '@prisma/client';\n"
                              "export const prisma = new PrismaClient();\n",
    "packages/web/src/App.tsx": d("""
        import { useEffect, useState } from 'react';
        import type { Shipment } from '@shipyard/shared/src/types';

        export default function App() {
          const [shipments, setShipments] = useState<Shipment[]>([]);
          useEffect(() => {
            fetch('/api/shipments').then(r => r.json()).then(setShipments);
          }, []);
          return <ul>{shipments.map(s => <li key={s.id}>{s.reference}</li>)}</ul>;
        }
    """),
    "packages/web/package.json": '{"name":"@shipyard/web","dependencies":'
                                 '{"react":"^18.3.0"}}\n',
}

# ═══════════════════════════════════════════════════════════════════════════
# 6. incomplete — half-built. The documenter must not present stubs as working.
# ═══════════════════════════════════════════════════════════════════════════
INCOMPLETE = {
    "README.md": d("""
        # Rosterly (WIP)

        Shift scheduling. **Early development — most of this does not work yet.**

        Done: employee CRUD, shift model.
        Not done: the scheduling algorithm, notifications, payroll export.
    """),
    "requirements.txt": "fastapi\nsqlalchemy\n",
    "app/main.py": d('''
        from fastapi import FastAPI

        from app.api import employees, shifts

        app = FastAPI(title="Rosterly")
        app.include_router(employees.router, prefix="/employees")
        app.include_router(shifts.router, prefix="/shifts")
        # TODO: schedule router once the solver works
    '''),
    "app/models.py": d('''
        import uuid
        from datetime import datetime

        from sqlalchemy import DateTime, ForeignKey, String
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


        class Base(DeclarativeBase):
            pass


        class Employee(Base):
            __tablename__ = "employees"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            name: Mapped[str] = mapped_column(String(200), nullable=False)
            hourly_rate_cents: Mapped[int] = mapped_column(nullable=False)


        class Shift(Base):
            __tablename__ = "shifts"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            employee_id: Mapped[uuid.UUID | None] = mapped_column(
                ForeignKey("employees.id"), nullable=True)
            starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
            ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

        # TODO: Availability model — blocked on deciding recurrence representation
    '''),
    "app/api/employees.py": d('''
        from fastapi import APIRouter

        router = APIRouter()


        @router.get("/")
        def list_employees():
            """Works."""
            ...


        @router.post("/")
        def create_employee(payload: dict):
            """Works."""
            ...
    '''),
    "app/api/shifts.py": d('''
        from fastapi import APIRouter

        router = APIRouter()


        @router.get("/")
        def list_shifts():
            """Works."""
            ...


        @router.post("/assign")
        def assign_shift(shift_id: str, employee_id: str):
            """NOT IMPLEMENTED. Returns 501."""
            raise NotImplementedError
    '''),
    "app/scheduling/solver.py": d('''
        """Shift assignment solver.

        Nothing here works. The whole module is a sketch of the intended
        approach and is not called from anywhere.
        """


        def build_schedule(employees, shifts, availability):
            raise NotImplementedError("solver not written")


        def score_assignment(assignment):
            raise NotImplementedError


        def _fairness_penalty(employee, assignment):
            # idea: penalise consecutive weekends
            raise NotImplementedError
    '''),
    "app/notifications.py": d('''
        """Notifications. Stub — no transport is wired up."""


        def notify_shift_assigned(employee_id, shift_id):
            pass  # TODO: email or push, undecided
    '''),
}

# ═══════════════════════════════════════════════════════════════════════════
# 7. mixed-stack — Python API + Node worker + Go CLI, one system.
# ═══════════════════════════════════════════════════════════════════════════
MIXED_STACK = {
    "README.md": d("""
        # Tilepipe

        Map tile rendering pipeline.

            api/      Python (FastAPI)  — accepts render jobs
            worker/   Node.js           — renders tiles, writes to S3
            cli/      Go                — operator tool for requeueing

        The three communicate through a Redis queue and a shared job schema.
    """),
    "api/requirements.txt": "fastapi\nredis\n",
    "api/main.py": d('''
        """Accepts tile render jobs and enqueues them."""
        import json
        import uuid

        import redis
        from fastapi import FastAPI

        app = FastAPI(title="Tilepipe API")
        r = redis.Redis(host="redis")

        QUEUE = "tilepipe:jobs"


        @app.post("/jobs")
        def create_job(payload: dict):
            job = {"id": str(uuid.uuid4()), "z": payload["z"],
                   "x": payload["x"], "y": payload["y"], "style": payload["style"]}
            r.lpush(QUEUE, json.dumps(job))
            return job


        @app.get("/jobs/{job_id}")
        def get_job(job_id: str):
            raw = r.get(f"tilepipe:result:{job_id}")
            return json.loads(raw) if raw else {"status": "pending"}
    '''),
    "worker/package.json": '{"name":"tilepipe-worker","dependencies":'
                           '{"ioredis":"^5.4.0","sharp":"^0.33.0"}}\n',
    "worker/index.js": d("""
        // Pulls jobs off the Redis queue, renders a tile, uploads it.
        const Redis = require('ioredis');
        const sharp = require('sharp');

        const redis = new Redis({ host: 'redis' });
        const QUEUE = 'tilepipe:jobs';

        async function main() {
          for (;;) {
            const [, raw] = await redis.brpop(QUEUE, 0);
            const job = JSON.parse(raw);
            try {
              const png = await render(job);
              await upload(job, png);
              await redis.set(`tilepipe:result:${job.id}`,
                              JSON.stringify({ status: 'done' }));
            } catch (err) {
              // No retry and no dead-letter queue — the job is simply lost.
              console.error('render failed', job.id, err);
            }
          }
        }

        async function render(job) { /* … */ }
        async function upload(job, png) { /* … */ }

        main();
    """),
    "cli/main.go": d("""
        // tilepipe-cli — operator tool for inspecting and requeueing jobs.
        package main

        import (
        	"context"
        	"flag"
        	"fmt"

        	"github.com/redis/go-redis/v9"
        )

        const queue = "tilepipe:jobs"

        func main() {
        	requeue := flag.String("requeue", "", "job id to requeue")
        	flag.Parse()

        	rdb := redis.NewClient(&redis.Options{Addr: "redis:6379"})
        	ctx := context.Background()

        	if *requeue != "" {
        		fmt.Println("requeued", *requeue)
        		_ = rdb.LPush(ctx, queue, *requeue).Err()
        		return
        	}
        	depth, _ := rdb.LLen(ctx, queue).Result()
        	fmt.Printf("queue depth: %d\\n", depth)
        }
    """),
}

# ═══════════════════════════════════════════════════════════════════════════
# 8. auth-heavy — roles, scopes, middleware. For authz documentation.
# ═══════════════════════════════════════════════════════════════════════════
AUTH_HEAVY = {
    "README.md": "# Vaultdesk\n\nDocument vault with role-based access.\n",
    "requirements.txt": "fastapi\npyjwt\nsqlalchemy\n",
    "app/auth/models.py": d('''
        """Roles, scopes and the join between them."""
        import uuid
        from enum import StrEnum

        from sqlalchemy import CheckConstraint, ForeignKey, String
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


        class Base(DeclarativeBase):
            pass


        class Role(StrEnum):
            VIEWER = "viewer"
            EDITOR = "editor"
            APPROVER = "approver"
            OWNER = "owner"
            AUDITOR = "auditor"


        # Higher number reaches further. Auditor sits outside the ladder.
        ROLE_RANK = {Role.VIEWER: 1, Role.EDITOR: 2,
                     Role.APPROVER: 3, Role.OWNER: 4}


        class User(Base):
            __tablename__ = "users"
            __table_args__ = (
                CheckConstraint(
                    "role IN ('viewer','editor','approver','owner','auditor')",
                    name="ck_users_role"),
            )
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            email: Mapped[str] = mapped_column(String(255), unique=True,
                                               nullable=False)
            role: Mapped[str] = mapped_column(String(20), nullable=False)
            org_id: Mapped[uuid.UUID] = mapped_column(
                ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)


        class Org(Base):
            __tablename__ = "orgs"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            name: Mapped[str] = mapped_column(String(200), nullable=False)
    '''),
    "app/auth/tokens.py": d('''
        """JWT issue and verify."""
        import datetime as dt

        import jwt

        SECRET = "change-me"          # loaded from env in deployment
        ALGORITHM = "HS256"
        ACCESS_TTL = dt.timedelta(minutes=15)
        REFRESH_TTL = dt.timedelta(days=14)


        def issue_access(user_id: str, role: str, org_id: str) -> str:
            now = dt.datetime.now(dt.UTC)
            return jwt.encode({"sub": user_id, "role": role, "org": org_id,
                               "iat": now, "exp": now + ACCESS_TTL,
                               "typ": "access"}, SECRET, algorithm=ALGORITHM)


        def issue_refresh(user_id: str) -> str:
            now = dt.datetime.now(dt.UTC)
            return jwt.encode({"sub": user_id, "iat": now,
                               "exp": now + REFRESH_TTL, "typ": "refresh"},
                              SECRET, algorithm=ALGORITHM)


        def verify(token: str) -> dict:
            """Decode and validate.

            Note: `typ` is not checked, so a refresh token is accepted anywhere
            an access token is expected.
            """
            return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    '''),
    "app/auth/policy.py": d('''
        """Authorisation policy. Every access decision goes through here."""
        from app.auth.models import ROLE_RANK, Role


        def can_read(user, document) -> bool:
            if user.role == Role.AUDITOR:
                return True                       # read-only, org-wide
            return document.org_id == user.org_id


        def can_edit(user, document) -> bool:
            if user.role == Role.AUDITOR:
                return False
            if document.org_id != user.org_id:
                return False
            return ROLE_RANK.get(user.role, 0) >= ROLE_RANK[Role.EDITOR]


        def can_approve(user, document) -> bool:
            if document.org_id != user.org_id:
                return False
            if document.created_by == user.id:
                return False                      # no self-approval
            return ROLE_RANK.get(user.role, 0) >= ROLE_RANK[Role.APPROVER]


        def can_delete(user, document) -> bool:
            return (document.org_id == user.org_id
                    and user.role == Role.OWNER)
    '''),
    "app/auth/deps.py": d('''
        """FastAPI dependencies. Scope is enforced here, not in endpoints."""
        from fastapi import Depends, Header, HTTPException

        from app.auth import tokens


        def current_user(authorization: str = Header(...)):
            if not authorization.startswith("Bearer "):
                raise HTTPException(401, "missing bearer token")
            try:
                claims = tokens.verify(authorization[7:])
            except Exception:
                raise HTTPException(401, "invalid token")
            return claims


        def require_role(*roles: str):
            def guard(user=Depends(current_user)):
                if user["role"] not in roles:
                    raise HTTPException(403, "insufficient role")
                return user
            return guard
    '''),
    "app/api/documents.py": d('''
        from fastapi import APIRouter, Depends

        from app.auth.deps import current_user, require_role

        router = APIRouter()


        @router.get("/")
        def list_documents(user=Depends(current_user)):
            """Org-scoped. Auditors see every org."""
            ...


        @router.post("/")
        def create_document(payload: dict,
                            user=Depends(require_role("editor", "approver",
                                                      "owner"))):
            ...


        @router.post("/{doc_id}/approve")
        def approve(doc_id: str,
                    user=Depends(require_role("approver", "owner"))):
            """Policy also refuses self-approval — see policy.can_approve."""
            ...


        @router.delete("/{doc_id}")
        def delete_document(doc_id: str, user=Depends(require_role("owner"))):
            ...
    '''),
}

# ═══════════════════════════════════════════════════════════════════════════
# 9. flow-heavy — a checkout with a clear multi-step call chain and a
#    transaction boundary worth drawing.
# ═══════════════════════════════════════════════════════════════════════════
FLOW_HEAVY = {
    "README.md": "# Cartline\n\nCheckout service. One flow, several steps.\n",
    "requirements.txt": "fastapi\nsqlalchemy\nstripe\n",
    "app/api/checkout.py": d('''
        from fastapi import APIRouter, Depends

        from app.services.checkout_service import CheckoutService, get_service

        router = APIRouter()


        @router.post("/checkout")
        def checkout(payload: dict, svc: CheckoutService = Depends(get_service)):
            """Single entry point for the whole flow."""
            return svc.checkout(payload["cart_id"], payload["payment_method"])
    '''),
    "app/services/checkout_service.py": d('''
        """Checkout. The ordering here matters and is easy to get wrong."""


        class CheckoutService:
            def __init__(self, db, inventory, payments, mailer, events):
                self._db = db
                self._inventory = inventory
                self._payments = payments
                self._mailer = mailer
                self._events = events

            def checkout(self, cart_id: str, payment_method: str):
                cart = self._load_cart(cart_id)
                self._validate(cart)

                # 1. Reserve stock — external call, before the transaction.
                reservation = self._inventory.reserve(cart.lines)

                try:
                    # 2. Transaction: order + lines + reservation reference.
                    with self._db.begin():
                        order = self._create_order(cart, reservation)
                        self._decrement_local_counters(cart)

                    # 3. Charge — AFTER commit. A failure here leaves a
                    #    committed order with no payment.
                    charge = self._payments.charge(order.total_cents,
                                                   payment_method)
                    self._mark_paid(order, charge)

                except Exception:
                    self._inventory.release(reservation)
                    raise

                # 4. Side effects, none of them transactional.
                self._mailer.send_confirmation(order)
                self._events.publish("order.created", order.id)
                return order

            def _load_cart(self, cart_id): ...
            def _validate(self, cart): ...
            def _create_order(self, cart, reservation): ...
            def _decrement_local_counters(self, cart): ...
            def _mark_paid(self, order, charge): ...


        def get_service(): ...
    '''),
    "app/services/inventory.py": d('''
        """Talks to the warehouse service over HTTP."""


        class InventoryClient:
            def reserve(self, lines):
                """POST /reservations. Returns a reservation id.

                No timeout is set on the underlying client.
                """
                ...

            def release(self, reservation_id):
                ...
    '''),
    "app/services/payments.py": d('''
        """Stripe wrapper."""


        class PaymentClient:
            def charge(self, amount_cents: int, method: str):
                """Creates a PaymentIntent and confirms it.

                Not idempotent — a retry double-charges.
                """
                ...
    '''),
    "app/models.py": d('''
        import uuid

        from sqlalchemy import ForeignKey, String
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


        class Base(DeclarativeBase):
            pass


        class Order(Base):
            __tablename__ = "orders"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            status: Mapped[str] = mapped_column(String(20), nullable=False,
                                                default="created")
            total_cents: Mapped[int] = mapped_column(nullable=False)
            reservation_id: Mapped[str | None] = mapped_column(String(64),
                                                               nullable=True)


        class OrderLine(Base):
            __tablename__ = "order_lines"
            id: Mapped[uuid.UUID] = mapped_column(primary_key=True,
                                                  default=uuid.uuid4)
            order_id: Mapped[uuid.UUID] = mapped_column(
                ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
            sku: Mapped[str] = mapped_column(String(40), nullable=False)
            quantity: Mapped[int] = mapped_column(nullable=False)
    '''),
}

FIXTURES = {
    "backend-only": (BACKEND_ONLY,
                     "FastAPI + SQLAlchemy + Alembic. Real schema, business-rule "
                     "CHECK constraints, divergent constraint names, no frontend."),
    "frontend-only": (FRONTEND_ONLY,
                      "React + TS + Vite. No server anywhere in the repo."),
    "no-database": (NO_DATABASE,
                    "Stateless service. Nothing persisted — a schema document "
                    "would be a fabrication."),
    "minimal-api": (MINIMAL_API,
                    "Two endpoints, one file. Tests proportionality."),
    "monorepo": (MONOREPO,
                 "Three packages, shared types, Prisma. Tests cross-package "
                 "contracts."),
    "incomplete": (INCOMPLETE,
                   "Half-built. Stubs raise NotImplementedError. Tests honesty "
                   "about what does not work."),
    "mixed-stack": (MIXED_STACK,
                    "Python + Node + Go around a Redis queue. Tests multi-language "
                    "coverage."),
    "auth-heavy": (AUTH_HEAVY,
                   "JWT, five roles, rank ladder, policy module. Tests authz "
                   "documentation."),
    "flow-heavy": (FLOW_HEAVY,
                   "Checkout with an explicit transaction boundary and unsafe "
                   "ordering. Tests sequence documentation."),
}


def write(name: str) -> str:
    files, _ = FIXTURES[name]
    root = os.path.join(OUT, name)
    if os.path.isdir(root):
        shutil.rmtree(root)
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf8", newline="\n") as fh:
            fh.write(content)
    return root


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--clean", action="store_true")
    args = ap.parse_args()

    if args.list:
        width = max(len(n) for n in FIXTURES)
        for name, (files, why) in FIXTURES.items():
            print(f"{name:<{width}}  {len(files):>2} files  {why}")
        return 0

    if args.clean:
        if os.path.isdir(OUT):
            shutil.rmtree(OUT)
        print(f"removed {OUT}")
        return 0

    names = args.only or list(FIXTURES)
    for name in names:
        if name not in FIXTURES:
            print(f"unknown fixture: {name}")
            return 1
        root = write(name)
        print(f"wrote {len(FIXTURES[name][0]):>2} files  {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

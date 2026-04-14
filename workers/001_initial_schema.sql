-- ============================================================
-- 001_initial_schema.sql
-- Smart Expense Analyzer - Initial database schema
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- 1. public.users
-- ============================================================
CREATE TABLE public.users (
    id         UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    email      TEXT NOT NULL,
    name       TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own" ON public.users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "users_insert_own" ON public.users
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "users_update_own" ON public.users
    FOR UPDATE USING (auth.uid() = id)
             WITH CHECK (auth.uid() = id);

-- ============================================================
-- 2. public.categories
-- ============================================================
CREATE TABLE public.categories (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    description TEXT
);

ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "categories_select_authenticated" ON public.categories
    FOR SELECT TO authenticated USING (true);

-- Seed default categories
INSERT INTO public.categories (name, description) VALUES
    ('Groceries',     'Supermarkets, farmers markets, and grocery stores'),
    ('Dining',        'Restaurants, cafes, fast food, and food delivery'),
    ('Transport',     'Public transit, rideshares, fuel, and parking'),
    ('Entertainment', 'Movies, concerts, streaming services, and events'),
    ('Utilities',     'Electricity, water, gas, internet, and phone bills'),
    ('Healthcare',    'Doctor visits, pharmacy, insurance, and wellness'),
    ('Shopping',      'Clothing, electronics, household items, and online shopping'),
    ('Education',     'Tuition, books, courses, and learning materials'),
    ('Travel',        'Flights, hotels, vacation packages, and travel expenses'),
    ('Other',         'Miscellaneous and uncategorized expenses');

-- ============================================================
-- 3. public.expenses
-- ============================================================
CREATE TABLE public.expenses (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    amount      NUMERIC(10, 2) NOT NULL,
    merchant    TEXT,
    category_id INTEGER REFERENCES public.categories (id),
    date        DATE NOT NULL DEFAULT CURRENT_DATE,
    raw_text    TEXT,
    image_path  TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'processed', 'manual_review', 'failed')),
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "expenses_select_own" ON public.expenses
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "expenses_insert_own" ON public.expenses
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "expenses_update_own" ON public.expenses
    FOR UPDATE USING (auth.uid() = user_id)
              WITH CHECK (auth.uid() = user_id);

CREATE POLICY "expenses_delete_own" ON public.expenses
    FOR DELETE USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX idx_expenses_user_id     ON public.expenses (user_id);
CREATE INDEX idx_expenses_status      ON public.expenses (status);
CREATE INDEX idx_expenses_user_date   ON public.expenses (user_id, date DESC);
CREATE INDEX idx_expenses_category_id ON public.expenses (category_id);

-- Auto-update trigger for updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_expenses_updated_at
    BEFORE UPDATE ON public.expenses
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- 4. public.predictions
-- ============================================================
CREATE TABLE public.predictions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    month               DATE NOT NULL,
    predicted_spend     NUMERIC(10, 2) NOT NULL,
    burnout_probability NUMERIC(5, 4) NOT NULL
                        CHECK (burnout_probability >= 0 AND burnout_probability <= 1),
    generated_at        TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "predictions_select_own" ON public.predictions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "predictions_insert_own" ON public.predictions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "predictions_delete_own" ON public.predictions
    FOR DELETE USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX idx_predictions_user_id    ON public.predictions (user_id);
CREATE INDEX idx_predictions_user_month ON public.predictions (user_id, month DESC);

-- ============================================================
-- 5. public.celery_tasks
-- ============================================================
CREATE TABLE public.celery_tasks (
    task_id      TEXT PRIMARY KEY,
    expense_id   UUID NOT NULL REFERENCES public.expenses (id) ON DELETE CASCADE,
    status       TEXT NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    result       JSONB,
    created_at   TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

ALTER TABLE public.celery_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "celery_tasks_select_own" ON public.celery_tasks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.expenses
            WHERE public.expenses.id = celery_tasks.expense_id
              AND public.expenses.user_id = auth.uid()
        )
    );

CREATE POLICY "celery_tasks_insert_own" ON public.celery_tasks
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.expenses
            WHERE public.expenses.id = celery_tasks.expense_id
              AND public.expenses.user_id = auth.uid()
        )
    );

CREATE POLICY "celery_tasks_update_own" ON public.celery_tasks
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.expenses
            WHERE public.expenses.id = celery_tasks.expense_id
              AND public.expenses.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.expenses
            WHERE public.expenses.id = celery_tasks.expense_id
              AND public.expenses.user_id = auth.uid()
        )
    );

-- Indexes
CREATE INDEX idx_celery_tasks_expense_id ON public.celery_tasks (expense_id);
CREATE INDEX idx_celery_tasks_status     ON public.celery_tasks (status);

-- ============================================================
-- Enable Supabase Realtime on expenses and celery_tasks
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.expenses;
ALTER PUBLICATION supabase_realtime ADD TABLE public.celery_tasks;

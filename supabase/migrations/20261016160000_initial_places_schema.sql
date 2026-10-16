create table public.campuses (
    id text primary key check (length(id) between 1 and 128),
    name text not null check (length(btrim(name)) between 1 and 200),
    created_at timestamptz not null default now()
);

create table public.places (
    id text primary key check (length(id) between 1 and 128),
    campus_id text not null references public.campuses (id) on delete restrict,
    name text not null check (length(btrim(name)) between 1 and 200),
    category text not null check (length(btrim(category)) between 1 and 64),
    description text,
    latitude numeric(9, 6) not null check (latitude between -90 and 90),
    longitude numeric(9, 6) not null check (longitude between -180 and 180),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index places_campus_id_idx on public.places (campus_id);

create function public.set_places_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = pg_catalog.now();
    return new;
end;
$$;

create trigger places_set_updated_at
before update on public.places
for each row
execute function public.set_places_updated_at();

create table public.entrances (
    id uuid primary key default gen_random_uuid(),
    place_id text not null references public.places (id) on delete cascade,
    description text not null check (length(btrim(description)) between 1 and 2000),
    latitude numeric(9, 6) check (latitude between -90 and 90),
    longitude numeric(9, 6) check (longitude between -180 and 180),
    photo_urls text[] not null default '{}',
    created_at timestamptz not null default now(),
    constraint entrances_coordinates_pair check (
        (latitude is null and longitude is null)
        or (latitude is not null and longitude is not null)
    )
);

create index entrances_place_id_idx on public.entrances (place_id);

create table public.facility_observations (
    id uuid primary key default gen_random_uuid(),
    place_id text not null references public.places (id) on delete cascade,
    facility text not null check (
        facility in (
            'step_free_entrance',
            'accessible_toilet',
            'designated_parking'
        )
    ),
    value text not null check (value in ('yes', 'no', 'unknown')),
    observed_at timestamptz,
    source text,
    notes text,
    evidence_urls text[] not null default '{}',
    recorded_at timestamptz not null default now()
);

create index facility_observations_place_facility_idx
    on public.facility_observations (place_id, facility, observed_at desc);

alter table public.campuses enable row level security;
alter table public.places enable row level security;
alter table public.entrances enable row level security;
alter table public.facility_observations enable row level security;

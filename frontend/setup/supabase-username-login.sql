-- Run once in Supabase > SQL Editor. Lets the Log in page accept a USERNAME as well as an email.
-- It returns only the email for one exact username, and only that.
create or replace function public.login_email(p_username text)
returns text language sql security definer stable set search_path = ''
as $$ select email::text from auth.users
      where lower(raw_user_meta_data->>'username') = lower(p_username) limit 1 $$;
revoke all on function public.login_email(text) from public;
grant execute on function public.login_email(text) to anon, authenticated;

-- OPTIONAL: if you created the example user ali@findr.test in the dashboard, give it the username "ali":
-- update auth.users set raw_user_meta_data = coalesce(raw_user_meta_data,'{}'::jsonb) || '{"username":"ali"}' where email = 'ali@findr.test';

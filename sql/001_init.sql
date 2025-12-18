create table if not exists hello (
  id bigserial primary key,
  message text not null
);

insert into hello(message) values ('Hello from Supabase 👋');

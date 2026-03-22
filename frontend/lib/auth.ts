import { supabase } from './supabase';

export const getSession = async () => {
  const { data: { session } } = await supabase.auth.getSession();
  return session;
};

export const getToken = async () => {
  const session = await getSession();
  return session?.access_token || null;
};

export const signOut = async () => {
  await supabase.auth.signOut();
  window.location.href = '/login';
};

export const getCurrentUser = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
};

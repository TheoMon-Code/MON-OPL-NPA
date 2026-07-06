// Netlify Scheduled Function — ping quotidien de Supabase
// Empêche la mise en pause du projet Supabase (plan gratuit) pour inactivité.
// S'exécute tous les jours à 01:00 UTC (08:00 heure de Bangkok).

export default async () => {
  const SUPABASE_URL = Netlify.env.get('SUPABASE_URL');
  const SUPABASE_KEY = Netlify.env.get('SUPABASE_ANON_KEY');

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.error('keep-alive: SUPABASE_URL / SUPABASE_ANON_KEY manquants');
    return new Response('missing env vars', { status: 500 });
  }

  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/employees?select=badge_number&limit=1`, {
      headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` }
    });
    console.log('keep-alive ping:', res.status);
    return new Response(res.ok ? 'ok' : `supabase error ${res.status}`, { status: res.ok ? 200 : 502 });
  } catch (e) {
    console.error('keep-alive failed:', e.message);
    return new Response('fetch failed', { status: 502 });
  }
};

export const config = {
  schedule: '0 1 * * *'
};

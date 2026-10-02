export default {
  async fetch(request, env) {
    const authHeader = request.headers.get('Authorization');
    if (authHeader !== `Bearer ${env.CLOUDFLARE_API_KEY}`) {
      return new Response('Unauthorized', { status: 401 });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    const incoming = await request.json();

    const body = {
      model: 'google/gemini-3.1-flash-lite',
      messages: incoming.messages,
      max_tokens: Math.min(incoming.max_tokens ?? 1000, 1000), // hard cap
      temperature: incoming.temperature ?? 0.0,
      provider: {zdr: true},
    };

    const upstream = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://csse.canterbury.ac.nz',
        'X-Title': 'AI feedback'
      },
      body: JSON.stringify(body),
    });

    return new Response(upstream.body, {
      headers: { 'Content-Type': 'application/json' },
      status: upstream.status
    });
  }
};
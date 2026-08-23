export default {
  async fetch(request, env, ctx) {
    return new Response("This is a dummy Cloudflare worker for LeadScraper", { status: 200 });
  },
};

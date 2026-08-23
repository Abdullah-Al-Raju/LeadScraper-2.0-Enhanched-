export default {
  async fetch(request, env, ctx) {
    return new Response("Python backend running.", { status: 200 });
  },
};

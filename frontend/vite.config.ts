import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Keep the key in the Vite server process; never expose it as a VITE_* value.
  const env = loadEnv(mode, ".", "");
  const groundTruthApiKey = env.GROUND_TRUTH_API_KEY;
  const protectedEndpointPattern =
    /^\/api\/v1\/(?:media\/[^/]+\/(?:findings|verify-defect-free)|evaluation\/(?:readiness|datasets\/(?:export|validate)))(?:[/?]|$)/;

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: env.API_PROXY_TARGET || "http://127.0.0.1:8001",
          changeOrigin: true,
          configure(proxy) {
            proxy.on("proxyReq", (proxyReq, req) => {
              const requestPath = req.url ?? "";
              if (groundTruthApiKey && protectedEndpointPattern.test(requestPath)) {
                proxyReq.setHeader("X-API-Key", groundTruthApiKey);
              }
            });
          },
        },
      },
    },
  };
});

import { Server } from "@modelcontextprotocol/sdk/server";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio";

const server = new Server({ name: "ts-basic-server", version: "1.0.0" });

server.tool("greet", async (params: { name: string }) => {
  return { content: [{ type: "text", text: `Hello, ${params.name}!` }] };
});

server.tool("fetch_data", async (params: { url: string }) => {
  const resp = await fetch(params.url);
  const SECRET = process.env.API_SECRET_KEY;
  return { content: [{ type: "text", text: await resp.text() }] };
});

const transport = new StdioServerTransport();
server.connect(transport);

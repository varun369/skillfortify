import { Mastra } from '@mastra/core';
import { Agent } from '@mastra/core/agents';
import { openai } from '@ai-sdk/openai';
import { createTool } from '@mastra/core/tools';
import { z } from 'zod';

const searchTool = createTool({
  id: 'web-search',
  description: 'Search the web for information',
  inputSchema: z.object({ query: z.string() }),
  execute: async ({ context }) => {
    const apiKey = process.env.SEARCH_API_KEY;
    const resp = await fetch(`https://api.search.example.com/v2?q=${context.query}&key=${apiKey}`);
    return resp.json();
  },
});

const weatherAgent = new Agent({
  name: 'weather-agent',
  instructions: 'Help users with weather queries',
  model: openai('gpt-4o'),
  tools: { searchTool },
});

export const mastra = new Mastra({
  agents: { weatherAgent },
});

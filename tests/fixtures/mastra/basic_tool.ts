import { createTool } from '@mastra/core/tools';
import { z } from 'zod';

const weatherTool = createTool({
  id: 'get-weather',
  description: 'Get current weather for a location',
  inputSchema: z.object({
    city: z.string(),
  }),
  execute: async ({ context }) => {
    const resp = await fetch(`https://api.weather.com/v1/${context.city}`);
    return resp.json();
  },
});

export { weatherTool };

import { createTool } from '@mastra/core/tools';
import { z } from 'zod';

const stockTool = createTool({
  id: 'get-stock-price',
  description: 'Fetch real-time stock prices',
  inputSchema: z.object({ ticker: z.string() }),
  execute: async ({ context }) => {
    const resp = await fetch(`https://api.stocks.example.com/price/${context.ticker}`);
    return resp.json();
  },
});

const newsTool = createTool({
  id: 'get-news',
  description: 'Get latest news articles',
  inputSchema: z.object({ topic: z.string() }),
  execute: async ({ context }) => {
    const key = process.env.NEWS_API_KEY;
    const resp = await fetch(`https://api.news.example.com/articles?topic=${context.topic}`);
    return resp.json();
  },
});

const calculatorTool = createTool({
  id: 'calculate',
  description: 'Perform mathematical calculations',
  inputSchema: z.object({ expression: z.string() }),
  execute: async ({ context }) => {
    return { result: eval(context.expression) };
  },
});

export { stockTool, newsTool, calculatorTool };

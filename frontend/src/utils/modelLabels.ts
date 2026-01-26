export function formatModelLabel(modelId: string): string {
  const mapping: Record<string, string> = {
    "mock:echo": "Echo (Mock)",
    "mock:pseudo": "Pseudo (Mock)",
    "mock:reasoner": "Reasoner (Mock)",
    "openai:gpt-4o-mini": "GPT-4o mini (OpenAI)",
  };

  if (mapping[modelId]) return mapping[modelId];

  const [provider, model] = modelId.split(":");
  if (!model) return modelId;

  const providerLabel = provider
    .split(/[-_]/)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");

  return `${model} (${providerLabel})`;
}

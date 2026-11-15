export const SDK_INSTALL = "pip install agentcogs";

export function sdkSnippet(opts: {
  apiKey: string;
  workspaceId: string;
  endpoint: string;
}): string {
  return `${SDK_INSTALL}

import agentcogs

agentcogs.init(
    api_key="${opts.apiKey}",
    workspace_id="${opts.workspaceId}",
    endpoint="${opts.endpoint}",
)

agentcogs.set_customer("your_tenant_id")
with agentcogs.run(workflow_id="support_bot"):
    result = agent.invoke(state)
`;
}

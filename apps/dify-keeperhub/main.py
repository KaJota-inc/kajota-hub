from dify_plugin import DifyPluginEnv, Plugin

# Onchain calls go through KeeperHub, which retries and manages nonces
# server-side; a short client timeout would abandon a call that is still
# settling rather than cancelling it.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=180))

if __name__ == "__main__":
    plugin.run()

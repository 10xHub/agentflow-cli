{
  "graphs": {
    "agent": "graph.react:app",
    "checkpointer": "graph.react:checkpointer",
    "store": "graph.store:store",
    "container": null
  },
  "env": ".env",
  "auth": null,
  "redis": "redis://localhost:6379/0"
}

# Supported Auth Methods
- "auth": null
- "auth": "jwt" # JWT-based authentication
it will check `JWT_SECRET_KEY` and `JWT_ALGORITHM` in environment variables
- "auth": "custom" # Custom authentication, in this case you need to implement your own auth logic and share the file path here
```
auth: {
    method: "custom",
    path: "/path/to/your/auth_module.py",
    user_id_mapping: "user_id" # Optional, default is "user_id"
}
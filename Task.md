Fix this ...

See the class should not be like this, 
api checking is not checking in sequence so we not able to capture the bugs
It should be invoke then using checkpointer api, we need to get the data

Lets execute api in below sequence, if any api fails then it should crash the script

# Test Graph APIs
1. /v1/ping/
2. /v1/graph
3. /v1/graph/StateSchema

# Test Graph Run APIs
1. /v1/graph/invoke
2. /v1/graph/stream

# Now checkpointer APIs
Note: using v1/graph/invoke will share thread_id, so we can use that thread_id to test checkpointer apis
1. /v1/threads/{thread_id}/state


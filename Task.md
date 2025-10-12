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


# Thinking blocks not converted to reasoning blocks

"thinking_blocks": [
                    {
                      "type": "thinking",
                      "thinking": "{\"text\": \"Hello! How can I help you today?\"}",
                      "signature": "CpwCAdHtim9umxTi9N+7hzmLhJnA1tIWY59EIk7d6FiZeBb/Faqtq7w7GxIqIeQQ08pNPtUOYDf5Vtl9FCc/dGP9a+QHmq2xoygtMEHY1e6tTDExoOeyDTWoL6/jruOoTTyUHxr62D2sD5xn/zmKmj7EGl5qDT5cJJRhPt208GvTchpA38QcazDAWIDzrkmqQEh+zdXv9HhUOM57yXs1/PDAPZiF20lVdEnGibqfsUa640o2tDVCxnd5xbciPdxEx6wrVhXVm0bnKybgXNPw+xory715t93vL0gY6h1MS8GGJbyVNO+xRwUD5yxCSG4HNyGdT9Axhfv8w8SNfG4IetJFegn2Oz8Us22PYm1bcH+7w/5yAJ2To4RHWO7TkeQ="
                    }
                  ]
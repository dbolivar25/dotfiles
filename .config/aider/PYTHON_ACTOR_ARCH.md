# Implementing Rust-Style Actor Architecture in Python

## Introduction

This guide presents a methodology for implementing an actor-based architecture in Python with asyncio that closely mirrors the approach used in Rust with Tokio. Rather than adapting the pattern to be more "Pythonic," this document focuses on direct translation of the architectural patterns, enabling developers familiar with Rust actor systems to implement the same patterns in Python.

Actor-based systems provide a powerful abstraction for concurrent programming by isolating components and enforcing communication through message passing. This reduces shared state complexity and minimizes the risk of race conditions.

## Core Architectural Components

The Rust implementation defines four core components for each actor:

1. **Actor struct**: Contains actor state and message handling logic
2. **Message enum**: Defines the message types that can be processed by the actor
3. **Handle struct**: Provides a clean API for interacting with the actor
4. **Runner function**: Manages the actor's event loop and lifecycle

We'll translate each of these components to Python while preserving their structure and relationships.

## Translating Actor Architecture to Python

### 1. Message Types

In Rust, messages are typically defined as enum variants:

```rust
pub enum KVStoreMessage {
    Set { key: Key, value: Value },
    Get { key: Key, respond_to: oneshot::Sender<Option<RESP3Value>> },
    Del { key: Key },
    Shutdown,
}
```

In Python, we can use classes with a namespace to mimic the enum structure:

```python
class KVStoreMessage:
    """Namespace for KVStore message types"""
    
    class Get:
        def __init__(self, key, respond_to=None):
            self.key = key
            self.respond_to = respond_to
    
    class Set:
        def __init__(self, key, value, ttl=None):
            self.key = key
            self.value = value
            self.ttl = ttl
    
    class Del:
        def __init__(self, key):
            self.key = key
    
    class Shutdown:
        def __init__(self, respond_to=None):
            self.respond_to = respond_to
```

This structure preserves the clear message-type definitions without using inheritance.

### 2. Actor Implementation

In Rust, actors are structs with methods for handling different message types:

```rust
pub struct KVStore {
    receiver: mpsc::Receiver<KVStoreMessage>,
    active_expiration_interval: Interval,
    kv_store: HashMap<Key, Value>,
}

impl KVStore {
    fn handle_message(&mut self, msg: KVStoreMessage) {
        match msg {
            KVStoreMessage::Set { key, value } => {
                // Handle set message
            },
            KVStoreMessage::Get { key, respond_to } => {
                // Handle get message
            },
            // Other message types...
        }
    }
}
```

In Python, this translates to:

```python
class KVStore:
    """Direct translation of the KVStore actor struct"""
    
    def __init__(self, receiver, active_expiration_interval):
        self.receiver = receiver
        self.active_expiration_interval = active_expiration_interval
        self.store = {}  # Equivalent to HashMap in Rust
        self.last_expiration_check = time.time()
    
    async def handle_message(self, message):
        """Handle a message from the receiver"""
        if isinstance(message, KVStoreMessage.Get):
            return await self.handle_get(message)
        elif isinstance(message, KVStoreMessage.Set):
            return await self.handle_set(message)
        elif isinstance(message, KVStoreMessage.Del):
            return await self.handle_del(message)
        elif isinstance(message, KVStoreMessage.Shutdown):
            return None
        else:
            raise ValueError(f"Unknown message type: {type(message)}")
    
    async def handle_get(self, message):
        """Handle a Get message"""
        # Implementation...
        value = self.store.get(message.key, (None, None))[0]
        return value
    
    async def handle_set(self, message):
        """Handle a Set message"""
        # Implementation...
        expiry = None
        if message.ttl:
            expiry = time.time() + message.ttl
        self.store[message.key] = (message.value, expiry)
        return "OK"
    
    async def handle_del(self, message):
        """Handle a Del message"""
        # Implementation...
        if message.key in self.store:
            del self.store[message.key]
        return "OK"
    
    def remove_expired(self, current_time):
        """Remove expired keys"""
        # Implementation (same logic as Rust version)
        expired_keys = [
            key for key, (_, expiry) in self.store.items()
            if expiry is not None and expiry <= current_time
        ]
        
        for key in expired_keys:
            del self.store[key]
```

### 3. Actor Handle

In Rust, handles provide a clean API for interacting with actors:

```rust
pub struct KVStoreHandle {
    sender: mpsc::Sender<KVStoreMessage>,
}

impl KVStoreHandle {
    pub async fn get(&self, key: Key) -> Result<Option<RESP3Value>> {
        let (respond_to, response) = oneshot::channel();
        let msg = KVStoreMessage::Get { key, respond_to };
        self.sender.send(msg).await?;
        response.await.map_err(Into::into)
    }
    
    // Other methods...
}
```

In Python, this translates to:

```python
class KVStoreHandle:
    """Handle for interacting with a KVStore actor"""
    
    def __init__(self, sender):
        self.sender = sender
    
    async def get(self, key):
        """Get a value from the KV store"""
        # Create oneshot channel equivalent
        response_future = asyncio.Future()
        
        # Create and send message
        message = KVStoreMessage.Get(key, response_future)
        await self.sender.put(message)
        
        # Wait for response
        return await response_future
    
    async def set(self, key, value, ttl=None):
        """Set a value in the KV store"""
        response_future = asyncio.Future()
        message = KVStoreMessage.Set(key, value, ttl)
        await self.sender.put(message)
        return await response_future
    
    async def delete(self, key):
        """Delete a value from the KV store"""
        response_future = asyncio.Future()
        message = KVStoreMessage.Del(key)
        await self.sender.put(message)
        return await response_future
    
    async def shutdown(self):
        """Shutdown the KV store actor"""
        response_future = asyncio.Future()
        message = KVStoreMessage.Shutdown(response_future)
        await self.sender.put(message)
        return await response_future
```

### 4. Actor Runner Function

In Rust, the runner function manages the event loop:

```rust
async fn run_kv_store(mut kv_store: KVStore, on_shutdown_complete: oneshot::Sender<()>) {
    log::info!("KV store started");

    loop {
        tokio::select! {
            msg = kv_store.receiver.recv() => match msg {
                Some(msg) => kv_store.handle_message(msg),
                None => break,
            },
            now = kv_store.active_expiration_interval.tick() => kv_store.remove_expired(now),
            else => {
                break;
            }
        }
    }

    log::info!("KV store shut down");
    on_shutdown_complete.send(()).ok();
}
```

In Python, this translates to:

```python
async def run_kv_store(kv_store, on_shutdown_complete):
    """Run the KV store actor"""
    print("KV store started")
    
    check_interval = kv_store.active_expiration_interval
    expiration_timer = time.time()
    
    try:
        while True:
            # Handle expiration timer
            current_time = time.time()
            if current_time - expiration_timer >= check_interval:
                kv_store.remove_expired(current_time)
                expiration_timer = current_time
            
            # Check for messages with timeout to handle expiration
            try:
                message = await asyncio.wait_for(
                    kv_store.receiver.get(), 
                    timeout=check_interval
                )
                
                # Process message
                result = await kv_store.handle_message(message)
                
                # Set response if message has a response channel
                if hasattr(message, 'respond_to') and message.respond_to is not None:
                    message.respond_to.set_result(result)
                
                # Mark message as processed
                kv_store.receiver.task_done()
                
                # Check for shutdown message
                if isinstance(message, KVStoreMessage.Shutdown):
                    break
                    
            except asyncio.TimeoutError:
                # This just means no message was available within our timeout
                # We use this to periodically check expiration
                pass
                
    except Exception as e:
        print(f"Error in KV store: {e}")
        # If there was an error and we have a response future, set the exception
        if hasattr(message, 'respond_to') and message.respond_to is not None:
            message.respond_to.set_exception(e)
    finally:
        print("KV store shut down")
        on_shutdown_complete.set_result(None)
```

### 5. Factory Function Pattern

The Rust implementation used factory functions to create actors and handles:

```rust
impl KVStoreHandle {
    pub fn new() -> (Self, oneshot::Receiver<()>) {
        let (sender, receiver) = mpsc::channel(32);
        let (on_shutdown_complete, shutdown_complete) = oneshot::channel();
        
        // Create KVStore and spawn task
        let kv_store = KVStore::new(receiver, ...);
        tokio::spawn(run_kv_store(kv_store, on_shutdown_complete));
        
        (KVStoreHandle { sender }, shutdown_complete)
    }
}
```

In Python, this translates to:

```python
def create_kv_store():
    """Create a KV store actor and its handle"""
    # Create message queue (equivalent to mpsc channel)
    queue = asyncio.Queue(maxsize=32)
    
    # Create shutdown signal (equivalent to oneshot channel)
    shutdown_complete = asyncio.Future()
    
    # Create the actor
    expiration_interval = 0.2  # 200ms
    kv_store = KVStore(queue, expiration_interval)
    
    # Spawn the runner task
    asyncio.create_task(run_kv_store(kv_store, shutdown_complete))
    
    # Create and return the handle
    return KVStoreHandle(queue), shutdown_complete
```

## Handling Multiple Event Sources

In Rust with Tokio, the `select!` macro elegantly handles multiple event sources. In Python's asyncio, we can use `asyncio.wait()` with `return_when=asyncio.FIRST_COMPLETED` to achieve similar behavior:

```python
async def run_connection(connection, on_shutdown_complete):
    """Run the connection actor"""
    print(f"Connection established for {connection.addr}")
    
    try:
        while True:
            # Create tasks for different event sources
            receiver_task = asyncio.create_task(
                connection.receiver.get(), 
                name="receiver"
            )
            
            stream_task = asyncio.create_task(
                connection.stream.readline(),
                name="stream"
            )
            
            # Wait for the first event to complete
            done, pending = await asyncio.wait(
                [receiver_task, stream_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Handle completed tasks
            for task in done:
                try:
                    result = task.result()
                    
                    # Handle message from queue
                    if task.get_name() == "receiver":
                        message = result
                        await connection.handle_message(message)
                        connection.receiver.task_done()
                        
                        # Check for shutdown message
                        if isinstance(message, ConnectionMessage.Shutdown):
                            raise StopAsyncIteration  # Break out of the loop
                    
                    # Handle data from stream
                    elif task.get_name() == "stream":
                        data = result
                        if not data:  # Connection closed
                            raise StopAsyncIteration  # Break out of the loop
                        
                        # Process network data
                        # ...
                
                except Exception as e:
                    if not isinstance(e, StopAsyncIteration):
                        print(f"Error processing task: {e}")
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    except StopAsyncIteration:
        # Normal exit path
        pass
    except Exception as e:
        print(f"Error in connection: {e}")
    finally:
        print(f"Connection closed for {connection.addr}")
        on_shutdown_complete.set_result(None)
```

## Error Handling

In Rust, errors are handled using the Result type. In Python, we use try/except blocks and set exceptions on Futures:

```python
async def handle_message(self, message):
    try:
        # Process message
        result = await self._process_specific_message(message)
        
        # Set result if we have a response channel
        if hasattr(message, 'respond_to') and message.respond_to is not None:
            if not message.respond_to.done():
                message.respond_to.set_result(result)
    except Exception as e:
        # Set exception on response future
        if hasattr(message, 'respond_to') and message.respond_to is not None:
            if not message.respond_to.done():
                message.respond_to.set_exception(e)
        # Optionally re-raise or log
        print(f"Error handling message: {e}")
```

## Complete Actor Implementation Example

Here's a complete implementation of a simple actor that maintains a counter:

```python
import asyncio
import time

# 1. Message Types
class CounterMessage:
    class Increment:
        def __init__(self, amount=1, respond_to=None):
            self.amount = amount
            self.respond_to = respond_to
    
    class Decrement:
        def __init__(self, amount=1, respond_to=None):
            self.amount = amount
            self.respond_to = respond_to
    
    class GetCount:
        def __init__(self, respond_to=None):
            self.respond_to = respond_to
    
    class Reset:
        def __init__(self, respond_to=None):
            self.respond_to = respond_to
    
    class Shutdown:
        def __init__(self, respond_to=None):
            self.respond_to = respond_to

# 2. Actor Implementation
class Counter:
    def __init__(self, receiver, initial_count=0):
        self.receiver = receiver
        self.count = initial_count
    
    async def handle_message(self, message):
        if isinstance(message, CounterMessage.Increment):
            self.count += message.amount
            return self.count
        elif isinstance(message, CounterMessage.Decrement):
            self.count -= message.amount
            return self.count
        elif isinstance(message, CounterMessage.GetCount):
            return self.count
        elif isinstance(message, CounterMessage.Reset):
            self.count = 0
            return self.count
        elif isinstance(message, CounterMessage.Shutdown):
            return None
        else:
            raise ValueError(f"Unknown message type: {type(message)}")

# 3. Actor Runner
async def run_counter(counter, on_shutdown_complete):
    print("Counter actor started")
    
    try:
        while True:
            # Get next message
            message = await counter.receiver.get()
            
            # Process message
            result = await counter.handle_message(message)
            
            # Set response if needed
            if hasattr(message, 'respond_to') and message.respond_to is not None:
                message.respond_to.set_result(result)
            
            # Mark message as processed
            counter.receiver.task_done()
            
            # Check for shutdown
            if isinstance(message, CounterMessage.Shutdown):
                break
    
    except Exception as e:
        print(f"Error in counter actor: {e}")
    finally:
        print("Counter actor shut down")
        on_shutdown_complete.set_result(None)

# 4. Actor Handle
class CounterHandle:
    def __init__(self, sender):
        self.sender = sender
    
    async def increment(self, amount=1):
        response_future = asyncio.Future()
        message = CounterMessage.Increment(amount, response_future)
        await self.sender.put(message)
        return await response_future
    
    async def decrement(self, amount=1):
        response_future = asyncio.Future()
        message = CounterMessage.Decrement(amount, response_future)
        await self.sender.put(message)
        return await response_future
    
    async def get_count(self):
        response_future = asyncio.Future()
        message = CounterMessage.GetCount(response_future)
        await self.sender.put(message)
        return await response_future
    
    async def reset(self):
        response_future = asyncio.Future()
        message = CounterMessage.Reset(response_future)
        await self.sender.put(message)
        return await response_future
    
    async def shutdown(self):
        response_future = asyncio.Future()
        message = CounterMessage.Shutdown(response_future)
        await self.sender.put(message)
        return await response_future

# 5. Factory Function
def create_counter(initial_count=0):
    queue = asyncio.Queue()
    shutdown_complete = asyncio.Future()
    
    counter = Counter(queue, initial_count)
    asyncio.create_task(run_counter(counter, shutdown_complete))
    
    return CounterHandle(queue), shutdown_complete

# Usage Example
async def main():
    # Create counter actor
    counter_handle, shutdown_complete = create_counter(initial_count=10)
    
    # Use the actor
    print(f"Initial count: {await counter_handle.get_count()}")
    print(f"After increment: {await counter_handle.increment(5)}")
    print(f"After decrement: {await counter_handle.decrement(2)}")
    print(f"After reset: {await counter_handle.reset()}")
    
    # Shutdown the actor
    await counter_handle.shutdown()
    
    # Wait for shutdown to complete
    await shutdown_complete
    print("Counter actor shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Patterns

### Multiple Actor Types Interaction

When multiple actor types need to interact, they do so through their handles:

```python
class WorkerActor:
    def __init__(self, receiver, logger_handle):
        self.receiver = receiver
        self.logger = logger_handle  # Handle to logger actor
    
    async def handle_message(self, message):
        if isinstance(message, WorkerMessage.DoWork):
            # Log through logger actor
            await self.logger.log(f"Starting work: {message.work_id}")
            
            # Do the work
            result = await self.do_work(message.work_id)
            
            # Log completion
            await self.logger.log(f"Completed work: {message.work_id}")
            
            return result
```

### Supervision and Lifecycle Management

To implement supervision patterns similar to Erlang/OTP:

```python
class SupervisorActor:
    def __init__(self, receiver):
        self.receiver = receiver
        self.children = {}  # Maps actor_id to (handle, shutdown_complete)
    
    async def handle_message(self, message):
        if isinstance(message, SupervisorMessage.StartChild):
            # Create child actor
            child_handle, shutdown_complete = create_worker()
            self.children[message.actor_id] = (child_handle, shutdown_complete)
            
            # Monitor child
            asyncio.create_task(self.monitor_child(message.actor_id, shutdown_complete))
            
            return child_handle
        
        elif isinstance(message, SupervisorMessage.StopChild):
            if message.actor_id in self.children:
                child_handle, _ = self.children[message.actor_id]
                await child_handle.shutdown()
                # Cleanup happens in monitor_child
            return None
    
    async def monitor_child(self, actor_id, shutdown_complete):
        # Wait for child to shut down
        await shutdown_complete
        
        # Remove from children
        if actor_id in self.children:
            del self.children[actor_id]
        
        print(f"Child {actor_id} has shut down")
```

## Performance Considerations

1. **Message Queue Size**: Adjust the maximum queue size based on expected message volume:
   ```python
   queue = asyncio.Queue(maxsize=1000)  # Larger queue for high-volume actors
   ```

2. **Task Priorities**: Use asyncio's task priorities where available:
   ```python
   task = asyncio.create_task(coro, name="high_priority")
   task.set_priority(asyncio.TaskPriority.HIGH)  # Python 3.11+
   ```

3. **Batching Messages**: For high-throughput systems, consider batching:
   ```python
   async def handle_batch(self, messages):
       results = []
       for message in messages:
           results.append(await self.handle_message(message))
       return results
   ```

4. **Proper Task Cancellation**: Always handle task cancellation cleanly:
   ```python
   for task in pending_tasks:
       task.cancel()
       try:
           await task
       except asyncio.CancelledError:
           pass  # Expected
   ```

## Conclusion

This approach directly translates the Rust actor model to Python, maintaining the same architecture, message passing patterns, and actor lifecycle management. While there are some syntactic differences due to language constraints, the core architecture remains intact.

The key benefits of this approach include:

1. **Clear Separation of Concerns**: Actors encapsulate state and behavior
2. **Message-Based Communication**: All interaction happens through typed messages
3. **Controlled Concurrency**: Each actor processes messages sequentially
4. **Clean API**: Handles provide a simple interface to actor functionality
5. **Proper Lifecycle Management**: Actors can be created and shut down cleanly

By following these patterns, you can build robust, concurrent systems in Python that leverage the actor model's strengths while maintaining a clear architectural approach that will be familiar to developers with experience in Rust actor systems.

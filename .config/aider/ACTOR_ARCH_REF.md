# Actor-Based Architecture Report: Redis Implementation in Rust

## Overview

This report analyzes the architecture of a Redis implementation in Rust located at `/Users/danielbolivar/Projects/rust/redis`. The project employs an elegant actor-based architecture with an efficient event loop design. This document focuses on the actor implementation approach and event loop mechanics to serve as a guide for implementing similar systems.

## Project Structure

The project is structured as a server-client Redis implementation with these main components:

- **Server**: Manages connection acceptance and coordinates lifecycle of key components
- **Connection Manager**: Handles client, master, and replica connections
- **Connection**: Represents individual client connections and processes Redis commands
- **KV Store**: Implements the actual key-value storage functionality

## Actor Pattern Implementation

### Core Components Pattern

Each actor in the system follows a consistent pattern consisting of four core components:

1. **Actor Struct**
   - Contains internal state
   - Has a receiver channel for incoming messages
   - Implements methods to handle different message types

2. **Message Enum**
   - Defines all possible operations the actor can perform
   - Each variant includes any data needed for that operation
   - Creates a clear API contract

3. **Handle Struct**
   - Provides a public API for interacting with the actor
   - Contains a sender channel to communicate with the actor
   - Methods map directly to message types
   - Cloneable for sharing across the system

4. **Runner Function**
   - Takes ownership of the actor
   - Runs in a dedicated Tokio task
   - Manages the actor's event loop
   - Handles actor lifecycle and cleanup

### Example: KVStore Actor

```rust
// 1. Actor Struct
pub struct KVStore {
    receiver: mpsc::Receiver<KVStoreMessage>,
    active_expiration_interval: Interval,
    kv_store: HashMap<Key, Value>,
}

// 2. Message Enum
pub enum KVStoreMessage {
    Set { key: Key, value: Value },
    Get { key: Key, respond_to: oneshot::Sender<Option<RESP3Value>> },
    Del { key: Key },
    Shutdown,
}

// 3. Handle Struct
pub struct KVStoreHandle {
    sender: mpsc::Sender<KVStoreMessage>,
}

// 4. Runner Function
async fn run_kv_store(mut kv_store: KVStore, on_shutdown_complete: oneshot::Sender<()>) {
    // Event loop implementation
    // ...
}
```

## Event Loop Design

The event loop is a critical component of each actor, implemented using Tokio's `select!` macro for efficient concurrent operation.

### Core Event Loop Pattern

```rust
async fn run_actor(mut actor: Actor, on_shutdown_complete: oneshot::Sender<()>) {
    loop {
        tokio::select! {
            // Process incoming messages from other actors
            msg = actor.receiver.recv() => match msg {
                Some(msg) => actor.handle_message(msg).await,
                None => break,
            },
            
            // Process other event sources (I/O, timers, etc.)
            event = actor.some_other_source.next() => {
                // Handle the event
            },
            
            // Break loop when all sources are exhausted
            else => break,
        }
    }
    
    // Cleanup and signal completion
    on_shutdown_complete.send(()).ok();
}
```

This pattern enables each actor to simultaneously:
- Process incoming messages from other components
- Handle I/O events (network data in Connection actors)
- Perform periodic tasks (expiration checks in KVStore)
- Respond to shutdown signals

## Message Passing System

The actor communication system employs two types of Tokio channels:

1. **MPSC Channels** (`mpsc::channel`)
   - Used for sending messages to actors
   - Multiple producers (handles) can send to a single consumer (actor)
   - Forms the backbone of actor communication

2. **Oneshot Channels** (`oneshot::channel`)
   - Used for responses that need to return a value
   - Used for signaling actor shutdown completion
   - Provides a lightweight way for one-time responses

### Request-Response Pattern

For operations requiring a response:

```rust
pub async fn get(&self, key: Key) -> Result<Option<RESP3Value>> {
    let (respond_to, response) = oneshot::channel();
    let msg = KVStoreMessage::Get { key, respond_to };
    self.sender.send(msg).await?;
    response.await.map_err(Into::into)
}
```

This pattern bundles both the request parameters and response channel in a single message, allowing the actor to directly respond to the caller.

## Actor Lifecycle Management

Each actor follows a well-defined lifecycle:

1. **Creation**:
   ```rust
   pub fn new() -> (Self, oneshot::Receiver<()>) {
       let (sender, receiver) = mpsc::channel(32);
       let (on_shutdown_complete, shutdown_complete) = oneshot::channel();
       
       let actor = Actor::new(receiver, /* other parameters */);
       tokio::spawn(run_actor(actor, on_shutdown_complete));
       
       (ActorHandle { sender }, shutdown_complete)
   }
   ```

2. **Shutdown**:
   ```rust
   pub async fn shutdown(&self) -> Result<()> {
       let msg = ActorMessage::Shutdown;
       self.sender.send(msg).await?;
       Ok(())
   }
   ```

3. **Confirmation**:
   ```rust
   // In the calling code
   actor_handle.shutdown().await?;
   let _ = shutdown_complete.await;
   ```

This approach ensures that resources are properly released and that the system can shut down gracefully.

## Error Handling

The actor system uses a consistent approach to error handling:

1. **Result Propagation**: Handle methods return `Result<T, E>` for operation success/failure
2. **Error Logging**: Internal errors are logged without necessarily stopping execution
3. **Inspection Pattern**: The `inspect_err` method logs errors while maintaining the error chain
4. **Response Channels**: Errors can be sent back via oneshot channels

## Actor Composition

The system has a well-defined actor hierarchy:

- **Server**: Top-level component that coordinates the system
- **ConnectionManager**: Manages all client, master, and replica connections
- **Connection**: Handles individual connections and command processing
- **KVStore**: Manages the actual data storage

This hierarchy creates a clean separation of concerns where each actor is responsible for a specific aspect of the system.

## Implementing Your Own Actor System

Based on this architecture, here's a guide for implementing your own actor-based system:

1. **Define your actors**: Identify components that can operate independently
2. **Create the message protocol**: Define clear message types for each actor
3. **Implement the handle API**: Design a clean, async interface for each actor
4. **Build the event loop**: Use Tokio's `select!` for efficient event handling
5. **Manage actor lifecycle**: Implement consistent creation and shutdown patterns
6. **Handle errors gracefully**: Use a combination of Result propagation and logging
7. **Define actor hierarchy**: Establish clear relationships between actors

## Conclusion

The actor-based architecture implemented in this Redis project provides an excellent template for building concurrent, message-driven systems in Rust. The combination of Tokio's async runtime with a well-designed actor model creates a robust and maintainable system that effectively handles the complexities of a distributed database.

The consistent patterns across actors, clean message-passing approach, and efficient event loop design make this architecture highly reusable for other projects requiring similar concurrency models.
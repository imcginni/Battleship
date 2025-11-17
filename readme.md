# Battleship Game: System Architecture

This document outlines the software architecture for the network-enabled Battleship game, including its offline (PvE) and online (PvP) modes.

The system is built on a client-server model for online play, with a modular design that allows for code reuse between different game modes.

---

## ## 1. Block Definition Diagram (BDD)

This SysML diagram shows the main components (blocks) of the system and their relationships.

* **`BattleshipServer`**: The headless Java application that acts as the "host" and authoritative source of truth for an online game.
* **`BattleshipClient`**: The Python $\text{Tkinter}$ application that players use. It contains the logic for both online (PvP) and offline (PvE) modes.
* **`CommonLogic`**: The shared Python file (`common.py`) that contains the data structures (like `PlayerBoard`) used by all other parts of the system.

```mermaid
bdd
    
    block BattleshipSystem {
        block BattleshipServer {
            +port 65432
            +handle_client()
            +send_to_all()
        }
        
        block BattleshipClient {
            +connect_to_server()
            +listen_to_server()
            +handle_server_message()
            +send_to_server()
        }
        
        block CommonLogic {
            +PlayerBoard
            +SHIP_SIZES
            +draw_grid_lines()
        }
    }
    
    BattleshipServer -- "1" hosts "2" -- BattleshipClient : "network_connection"
    BattleshipServer ..> CommonLogic : "uses"
    BattleshipClient ..> CommonLogic : "uses"
```

---

## ## 2. Sequence Diagram (Online Attack)

This diagram shows the "how" and "when" of communication for a complete turn in the online (PvP) mode.

This example covers **Player 1 firing a shot that HITS**, allowing them to go again, and then **firing a shot that MISSES**, causing the turn to change.

```mermaid
sequenceDiagram
    participant P1 as Player_1_Client
    participant SRV as Battleship_Server
    participant P2 as Player_2_Client
    
    Note over P1, P2: Game is in Attack Phase. It is P1's turn.

    %% --- P1 Fires and HITS ---
    P1->>+SRV: send_to_server( {type: 'SHOT', col: 3, row: 4} )
    
    Note over SRV: Processes shot against P2's board...<br/>Result is a HIT.
    
    SRV->>-P1: send_to_client( {type: 'SHOT_RESULT', result: 'Hit'} )
    SRV->>-P2: send_to_client( {type: 'OPPONENT_SHOT', ...} )
    
    Note over P1: GUI updates to show 'HIT!'<br/>GUI click is re-enabled.
    Note over P2: GUI updates to show damage on their board.
    
    SRV->>P1: send_to_client( {type: 'YOUR_TURN'} )
    
    Note over P1: Player clicks again.
    
    %% --- P1 Fires and MISSES ---
    P1->>+SRV: send_to_server( {type: 'SHOT', col: 5, row: 5} )
    
    Note over SRV: Processes shot against P2's board...<br/>Result is a MISS.
    
    SRV->>-P1: send_to_client( {type: 'SHOT_RESULT', result: 'Miss'} )
    SRV->>-P2: send_to_client( {type: 'OPPONENT_SHOT', ...} )
    
    Note over P1: GUI updates to show 'MISS.'<br/>GUI click is not re-enabled.
    Note over P2: GUI updates to show the miss.
    
    %% --- Turn Change ---
    SRV->>P1: send_to_client( {type: 'OPPONENT_TURN'} )
    SRV->>P2: send_to_client( {type: 'YOUR_TURN'} )
    
    Note over P1, P2: P1's GUI is now locked. P2's GUI is unlocked.
```

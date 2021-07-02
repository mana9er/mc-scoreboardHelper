# mc-scoreboardHelper
A Minecraft [mana9er](https://github.com/mana9er/mana9er-core) plugin for enabling in-game sidebar scoreboard cycling.

## Functionalities & Usage

The following shows a list of functionalities of the ***scoreboardHelper*** pulgin and their in-game usages (by sending the command to the chat box).

### For Players

1. List all visible scoreboards.

   ```
   !sb list
   ```

2. View a certain scoreboard for a (fixed) period of time.

   ```
   !sb view <name>
   ```

3. Display help info.

   ```
   !sb help
   ```

### For Server OPerators

1. Toggle scoreboard cycling.

   ```
   !sb cycle <true|false>
   ```

2. Register / Remove "visible" scoreboards.

   ```
   !sb <add|rm> visible <name>
   ```

3. Register / Remove scoreboards for cycling.

   ```
   !sb <add|rm> cycle <name>
   ```

4. Set scoreboard cycle interval.

   ```
   !sb settime cycle <time_in_sec>
   ```

5. Set duration for temporal viewing.

   ```
   !sb settime view <time_in_sec>
   ```

   


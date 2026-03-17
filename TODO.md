# Tennis Simulator — To-Do List

## Bugs
- [ ] `update_camera` callback does not update the global `camera` variable (missing `global camera` declaration and `Output`)
- [ ] `load_preset` references `dash` without importing it (`dash.exceptions.PreventUpdate`)
- [ ] Landing depth reports distance from opponent's baseline but does not account for impact position offset (`impact_x`)

## Features
- [ ] Add serve simulation mode (ball toss, racket contact point)
- [ ] Show ball speed at net and at bounce in the metrics panel
- [ ] Add side-by-side comparison mode (overlay up to N shots with different colors)
- [ ] Support left-handed / mirrored court view
- [ ] Export trajectory data as CSV
- [ ] Animate the ball along the trajectory (play/pause button)
- [ ] Add court dimensions for doubles (alleys)
- [ ] Show in/out indicator based on landing position

## UI / UX
- [ ] Make the drawer resizable on mobile (touch support for `#resize` handle)
- [ ] Persist slider values in URL query params so shots can be shared via link
- [ ] Add a "Reset to defaults" button for all sliders
- [ ] Show a mini top-down court map with the landing spot marked

## Physics
- [ ] Validate Magnus force coefficient against published data
- [ ] Add wind speed / direction parameter
- [ ] Model racket string type effect on coefficient of restitution

## Code Quality
- [ ] Add type hints to `simulate()` and `plot_court_fig()`
- [ ] Write unit tests for `compute_net_clearance` and `compute_landing_depth`
- [ ] Move layout constants (colors, court dimensions) to a dedicated `constants.py`
- [ ] Remove debug `print` statements in the `update` callback

// ACCESS FEATURES SHOWN ON THE SITE. Keys must match the backend's facility names.
// Adding a line here adds a filter checkbox, a status row and a contribution option automatically.
// NOTE: the backend currently knows only the first three (see INTEGRATION.md). The rest show "Not checked yet".
export const FACILITIES = [
  { key: 'step_free_entrance',   label: 'Step-free entrance' },
  { key: 'accessible_toilet',    label: 'Accessible toilet' },
  { key: 'designated_parking',   label: 'Parking' },
  { key: 'lift',                 label: 'Lift' },
  { key: 'braille',              label: 'Braille signs' },
  { key: 'flashing_fire_alarm',  label: 'Flashing fire alarm' },
  { key: 'tactile_paving',       label: 'Tactile paving to entrance' }
]

// Status look. Colour is never the only signal: each has an icon and a word.
export const STATUS = {
  yes: { text: 'Yes', icon: '✔', cls: 'text-yes' },
  no: { text: 'No', icon: '✖', cls: 'text-no' },
  unknown: { text: 'Not checked yet', icon: '?', cls: 'text-unknown' }
}

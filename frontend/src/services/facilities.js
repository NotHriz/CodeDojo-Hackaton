// ACCESS FEATURES SHOWN ON THE SITE. Keys must match the backend's facility names.
// Adding a line here adds a filter checkbox, a status row and a contribution option automatically.
// Keep this vocabulary aligned with the database CHECK constraint and API schema.
export const FACILITIES = [
  { key: 'step_free_entrance',   label: 'Step-free entrance' },
  { key: 'accessible_toilet',    label: 'Accessible toilet' },
  { key: 'designated_parking',   label: 'Parking' }
]

// Status look. Colour is never the only signal: each has an icon and a word.
export const STATUS = {
  yes: { text: 'Yes', icon: '✔', cls: 'text-yes' },
  no: { text: 'No', icon: '✖', cls: 'text-no' },
  unknown: { text: 'Not checked yet', icon: '?', cls: 'text-unknown' }
}

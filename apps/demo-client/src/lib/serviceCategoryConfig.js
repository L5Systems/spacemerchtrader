export const RECORD_STATUSES = ['draft', 'active', 'completed', 'cancelled'];

export const SERVICE_WORKSPACES = {
  container_assembly: {
    label: 'Container Assembly',
    recordLabel: 'Container',
    summaryField: 'container_code',
    fields: [
      { key: 'container_code', label: 'Container code', required: true, placeholder: 'CNT-SOL-001' },
      { key: 'owner_name', label: 'Owner name', required: true, placeholder: 'Aurora Trading Co.' },
      { key: 'system_id', label: 'System', type: 'system', required: true },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
    packages: {
      label: 'Package',
      fields: [
        { key: 'package_id', label: 'Package ID', required: true, placeholder: 'PKG-8842' },
        { key: 'owner_name', label: 'Owner name', required: true },
        { key: 'recipient_name', label: 'Recipient name', required: true },
        { key: 'recipient_id', label: 'Recipient ID', required: true, placeholder: 'RCPT-230' },
        { key: 'address', label: 'Address', required: true, placeholder: 'Starship239 Factory Ring, LEO' },
        {
          key: 'manifest_leg',
          label: 'Manifest leg',
          type: 'leg',
          placeholder: 'outbound or return',
        },
        { key: 'notes', label: 'Notes', type: 'textarea' },
      ],
    },
  },
  container_collection: {
    label: 'Container Collection',
    recordLabel: 'Collection job',
    summaryField: 'job_code',
    pickupAction: true,
    fields: [
      { key: 'job_code', label: 'Job code', required: true, placeholder: 'COL-SOL-001' },
      { key: 'container_code', label: 'Container code', required: true, placeholder: 'CNT-SOL-001' },
      { key: 'contractor_id', label: 'Offshore contractor', type: 'contractor', required: true },
      { key: 'system_id', label: 'System', type: 'system', required: true },
      {
        key: 'pickup_site',
        label: 'Pickup site',
        required: true,
        placeholder: 'Offshore Platform 7, Sol Drift',
      },
      { key: 'owner_name', label: 'Owner name', required: true },
      { key: 'package_id', label: 'Package ID', placeholder: 'PKG-8842' },
      { key: 'recipient_name', label: 'Recipient name' },
      { key: 'recipient_id', label: 'Recipient ID' },
      {
        key: 'delivery_address',
        label: 'Delivery address',
        placeholder: 'Lab 230, Starship 4090',
      },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
  },
  container_aggregator: {
    label: 'Container Aggregator',
    recordLabel: 'Launch stack',
    summaryField: 'stack_code',
    fields: [
      { key: 'stack_code', label: 'Stack code', required: true, placeholder: 'STK-001' },
      { key: 'system_id', label: 'System', type: 'system', required: true },
      {
        key: 'container_codes',
        label: 'Container codes',
        placeholder: 'CNT-SOL-001, CNT-SOL-002',
      },
      { key: 'target_orbit', label: 'Target orbit', placeholder: 'LEO transfer' },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
  },
  ground_launch: {
    label: 'Ground Launch',
    recordLabel: 'Launch booking',
    summaryField: 'booking_code',
    fields: [
      { key: 'booking_code', label: 'Booking code', required: true },
      { key: 'pad_location', label: 'Pad location', required: true, placeholder: 'Sol Pad 7' },
      { key: 'launch_window', label: 'Launch window', required: true, placeholder: '2026-07-01 14:00 UTC' },
      { key: 'payload_ref', label: 'Payload ref', placeholder: 'STK-001' },
      { key: 'mass_kg', label: 'Mass (kg)', type: 'number' },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
  },
  container_porter: {
    label: 'Container Porter',
    recordLabel: 'Porter job',
    summaryField: 'job_code',
    fields: [
      { key: 'job_code', label: 'Job code', required: true },
      { key: 'container_code', label: 'Container code', required: true },
      { key: 'owner_name', label: 'Owner name', required: true },
      { key: 'package_id', label: 'Package ID' },
      { key: 'recipient_name', label: 'Recipient name' },
      { key: 'recipient_id', label: 'Recipient ID' },
      { key: 'origin_address', label: 'Origin address', required: true, placeholder: 'Dock A, Bay 12' },
      {
        key: 'destination_address',
        label: 'Destination address',
        required: true,
        placeholder: 'Lab 230, Starship 4090',
      },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
  },
  offworld_endpoint: {
    label: 'Offworld Endpoint',
    recordLabel: 'Endpoint receipt',
    summaryField: 'receipt_code',
    fields: [
      { key: 'receipt_code', label: 'Receipt code', required: true },
      { key: 'container_code', label: 'Container code', required: true },
      { key: 'package_id', label: 'Package ID', required: true },
      { key: 'owner_name', label: 'Owner name', required: true },
      { key: 'recipient_name', label: 'Recipient name', required: true },
      { key: 'recipient_id', label: 'Recipient ID', required: true },
      {
        key: 'gateway_address',
        label: 'Gateway address',
        required: true,
        placeholder: 'Kepler Gate Terminal, Rim Dock 3',
      },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
  },
  offworld_delivery: {
    label: 'Offworld Delivery',
    recordLabel: 'Delivery order',
    summaryField: 'delivery_code',
    fields: [
      { key: 'delivery_code', label: 'Delivery code', required: true },
      { key: 'package_id', label: 'Package ID', required: true },
      { key: 'owner_name', label: 'Owner name', required: true },
      { key: 'recipient_name', label: 'Recipient name', required: true },
      { key: 'recipient_id', label: 'Recipient ID', required: true },
      {
        key: 'destination_address',
        label: 'Destination address',
        required: true,
        placeholder: 'Lab 230, Starship 4090',
      },
      { key: 'status', label: 'Status', type: 'status' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
  },
};

/** @param {string} category */
export function getWorkspaceConfig(category) {
  return SERVICE_WORKSPACES[category] ?? null;
}

/** @param {Array<{key: string, type?: string}>} fields */
export function emptyForm(fields) {
  /** @type {Record<string, string>} */
  const form = {};
  for (const field of fields) {
    if (field.type === 'status') form[field.key] = 'draft';
    else if (field.type === 'number') form[field.key] = '0';
    else form[field.key] = '';
  }
  return form;
}

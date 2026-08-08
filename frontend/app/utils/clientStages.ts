export const CLIENT_TYPES = ['seller', 'buyer'] as const
export type ClientType = typeof CLIENT_TYPES[number]

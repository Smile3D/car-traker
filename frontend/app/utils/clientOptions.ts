export const CLIENT_LEAD_SOURCES = ['tiktok', 'instagram', 'facebook', 'referral', 'saw_ad_online'] as const
export type ClientLeadSource = typeof CLIENT_LEAD_SOURCES[number]

const LEAD_SOURCE_LABEL_KEYS: Record<ClientLeadSource, string> = {
    tiktok: 'clientOptions.leadSource.tiktok',
    instagram: 'clientOptions.leadSource.instagram',
    facebook: 'clientOptions.leadSource.facebook',
    referral: 'clientOptions.leadSource.referral',
    saw_ad_online: 'clientOptions.leadSource.sawAdOnline',
}

export function getLeadSourceLabelKey(value: ClientLeadSource): string {
    return LEAD_SOURCE_LABEL_KEYS[value]
}

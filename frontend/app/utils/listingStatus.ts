import type { ListingStatus } from '~/types/listings'

export function getListingStatusBadgeClasses(status: ListingStatus): string {
  switch (status) {
    case 'active':
      return 'bg-success/10 text-success'
    case 'reserved':
      return 'bg-amber-500/10 text-amber-600'
    case 'sold':
      return 'bg-blue-500/10 text-blue-600'
    case 'removed':
      return 'bg-destructive/10 text-destructive'
    case 'on_service':
      return 'bg-violet-500/10 text-violet-600'
    case 'draft':
    default:
      return 'bg-muted text-muted-foreground'
  }
}

export function calculateTotalCost(purchasePrice: number, additionalExpenses: number): number {
  return purchasePrice + additionalExpenses
}

export function calculateFinalPrice(salePrice: number, discountAmount: number): number {
  return salePrice - discountAmount
}

export function calculateNetProfit(revenue: number, totalCost: number): number {
  return revenue - totalCost
}

import React from 'react'
import TanStackDataTable from './TanStackDataTable'

interface SellerInfo {
  SellerName?: string
  SellerType?: string
  Packaging?: any[]
}

interface MarketData {
  PartId?: string
  PartNumber?: string
  NumberOfSeller?: number
  MarketStatus?: string
  GeneralMarketStatus?: string
  MarketLeadTime_weeks?: string
  Sellers?: SellerInfo[]
  [key: string]: any
}

interface MarketAvailabilityDisplayProps {
  data: MarketData[]
  part_number?: string
  manufacturer?: string
}

const MarketAvailabilityDisplay: React.FC<MarketAvailabilityDisplayProps> = ({ data, part_number, manufacturer }) => {
  if (!data || data.length === 0) {
    return <div>No market availability data</div>
  }

  const marketInfo = data[0]
  const sellers = marketInfo.Sellers || []

  // Create transposed data excluding PartId and Sellers
  const transposedData = Object.entries(marketInfo)
    .filter(([key]) => key !== 'PartId' && key !== 'Sellers')
    .map(([key, value]) => ({
      field: key.replace(/([A-Z])/g, ' $1').trim().replace(/_/g, ' '),
      value: value?.toString() || ''
    }))

  return (
    <div style={{ width: '100%' }}>
      {/* Seller Cards */}
      {sellers.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{
            fontSize: '16px',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '16px'
          }}>
            Available Distributors
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '16px'
          }}>
            {sellers.map((seller, idx) => (
              <div key={idx} style={{
                background: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '16px',
                boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)'
              }}>
                <div style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#111827',
                  marginBottom: '4px'
                }}>
                  {seller.SellerName || 'Unknown Distributor'}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#6b7280',
                  marginBottom: '12px'
                }}>
                  {seller.SellerType || 'Distributor'}
                </div>

                {seller.Packaging && seller.Packaging.length > 0 && (
                  <div style={{ marginTop: '8px' }}>
                    {seller.Packaging.map((pkg: any, pkgIdx: number) => (
                      <div key={pkgIdx} style={{
                        padding: '8px',
                        background: '#f9fafb',
                        borderRadius: '4px',
                        marginBottom: '8px'
                      }}>
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '6px'
                        }}>
                          <div style={{ fontSize: '12px', color: '#374151' }}>
                            {pkg.SKU || 'N/A'}
                          </div>
                          <div style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            color: pkg.Stock > 0 ? '#059669' : '#dc2626'
                          }}>
                            Stock: {pkg.Stock || 0}
                          </div>
                        </div>

                        {pkg.PackageType && (
                          <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px' }}>
                            Package: {pkg.PackageType}
                          </div>
                        )}

                        {pkg.LeadTime && (
                          <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '4px' }}>
                            Lead Time: {pkg.LeadTime}
                          </div>
                        )}

                        {pkg.PackagePrices && pkg.PackagePrices.length > 0 && (
                          <div style={{
                            fontSize: '11px',
                            color: '#374151',
                            marginTop: '6px',
                            paddingTop: '6px',
                            borderTop: '1px solid #e5e7eb'
                          }}>
                            <div style={{ fontWeight: '500', marginBottom: '4px' }}>Pricing:</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                              {pkg.PackagePrices.slice(0, 3).map((price: any, priceIdx: number) => (
                                <div key={priceIdx} style={{
                                  background: 'white',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  border: '1px solid #e5e7eb'
                                }}>
                                  {price.PriceBreak}+: ${price.Price}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {pkg.BuyNowLink && (() => {
                          // Extract URL from BuyNowLink
                          // Some sellers send "price1,price2,,,URL" format
                          let url = pkg.BuyNowLink
                          if (url.includes(',,,')) {
                            const parts = url.split(',,,')
                            url = parts[parts.length - 1]
                          }
                          // Ensure URL starts with http
                          if (!url.startsWith('http://') && !url.startsWith('https://')) {
                            url = 'https://' + url
                          }
                          return (
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                display: 'inline-block',
                                marginTop: '8px',
                                padding: '4px 12px',
                                background: '#3b82f6',
                                color: 'white',
                                borderRadius: '4px',
                                fontSize: '11px',
                                textDecoration: 'none',
                                fontWeight: '500'
                              }}
                            >
                              Buy Now →
                            </a>
                          )
                        })()}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Market Availability Table */}
      <div style={{ marginTop: '20px' }}>
        <h3 style={{
          fontSize: '16px',
          fontWeight: '600',
          color: '#374151',
          marginBottom: '12px'
        }}>
          Market Information
        </h3>
        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          overflow: 'hidden'
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {transposedData.map((row, idx) => (
                <tr key={idx} style={{
                  borderBottom: idx < transposedData.length - 1 ? '1px solid #f3f4f6' : 'none'
                }}>
                  <td style={{
                    padding: '12px 16px',
                    fontSize: '13px',
                    fontWeight: '500',
                    color: '#6b7280',
                    width: '200px',
                    background: '#f9fafb'
                  }}>
                    {row.field}
                  </td>
                  <td style={{
                    padding: '12px 16px',
                    fontSize: '13px',
                    color: '#111827'
                  }}>
                    {row.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default MarketAvailabilityDisplay
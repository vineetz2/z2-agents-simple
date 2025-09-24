import React, { useMemo } from 'react';
import TanStackDataTable from './TanStackDataTable';
import './App.css';

interface PartDetailsDisplayProps {
  data: any;
  userQuery?: string;
}

const PartDetailsDisplay: React.FC<PartDetailsDisplayProps> = ({ data, userQuery }) => {
  // Extract the structured data from the tool response
  const extractedData = useMemo(() => {
    // Handle various response structures
    let partData = data;

    // Handle wrapper structures
    if (data?.results && Array.isArray(data.results)) {
      const successfulResult = data.results.find((r: any) => r.success && r.result);
      if (successfulResult?.result?.results) {
        partData = successfulResult.result.results;
      } else if (successfulResult?.result) {
        partData = successfulResult.result;
      }
    } else if (data?.result?.results) {
      partData = data.result.results;
    } else if (data?.result) {
      partData = data.result;
    } else if (data?.results && !Array.isArray(data.results)) {
      partData = data.results;
    }

    return partData;
  }, [data]);

  if (!extractedData || typeof extractedData !== 'object') {
    return null;
  }

  // Helper function to create summary data for key-value pairs
  const createSummaryData = (obj: any, excludeKeys: string[] = []) => {
    if (!obj || typeof obj !== 'object') return [];

    return Object.entries(obj)
      .filter(([key]) => !excludeKeys.includes(key))
      .map(([key, value]) => ({
        Property: formatPropertyName(key),
        Value: formatValue(value)
      }));
  };

  // Helper function to format property names (fixing letter spacing issues)
  const formatPropertyName = (key: string): string => {
    // Fix letter spacing issues by properly handling camelCase and special cases
    let formatted = key
      // Handle common API field patterns
      .replace(/([a-z])([A-Z])/g, '$1 $2')  // camelCase -> camel Case
      .replace(/([A-Z])([A-Z][a-z])/g, '$1 $2')  // XMLHttpRequest -> XML Http Request
      .replace(/\bID\b/g, 'ID')  // Keep ID together
      .replace(/\bMPN\b/g, 'MPN')  // Keep MPN together
      .replace(/\bURL\b/g, 'URL')  // Keep URL together
      .replace(/\bAPI\b/g, 'API')  // Keep API together
      .replace(/\bEOL\b/g, 'EOL')  // Keep EOL together
      .replace(/\bPCN\b/g, 'PCN')  // Keep PCN together
      .replace(/\bLC\b/g, 'LC')  // Keep LC together
      .trim();

    // Capitalize first letter
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  };

  // Helper function to format values
  const formatValue = (value: any): any => {
    if (value === null || value === undefined) return 'N/A';
    if (Array.isArray(value)) {
      if (value.length === 0) return 'None';
      // Preserve URLs in arrays for TanStackDataTable to handle
      if (typeof value[0] === 'string' && value.every(item =>
        typeof item === 'string' && (item.startsWith('http://') || item.startsWith('https://'))
      )) {
        return value; // Return the array as-is for URL handling
      }
      if (typeof value[0] === 'string') return value.join(', ');
      return `${value.length} items`;
    }
    if (typeof value === 'object') {
      return Object.keys(value).length + ' properties';
    }
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    // Preserve URLs as-is for TanStackDataTable to handle
    if (typeof value === 'string' && (value.startsWith('http://') || value.startsWith('https://'))) {
      return value; // Return URL as-is
    }
    return String(value);
  };

  // Prepare data sections
  const sections = [];

  // 1. MPN Summary (Basic Part Information)
  if (extractedData.MPNSummary) {
    const summaryData = createSummaryData(extractedData.MPNSummary);

    // Add Part Image if available
    if (extractedData.MPNSummary.PartImage) {
      summaryData.unshift({
        Property: 'Part Image',
        Value: extractedData.MPNSummary.PartImage
      });
    }

    sections.push({
      title: 'Part Summary',
      data: summaryData,
      priority: 1
    });
  }

  // 2. Lifecycle Information
  if (extractedData.Lifecycle) {
    sections.push({
      title: 'Lifecycle Status',
      data: createSummaryData(extractedData.Lifecycle),
      priority: 2
    });
  }

  // 3. Risk Scores
  if (extractedData.MPNRiskScore) {
    sections.push({
      title: 'Risk Assessment',
      data: createSummaryData(extractedData.MPNRiskScore),
      priority: 3
    });
  }

  // 4. Compliance Details
  if (extractedData.ComplianceDetails) {
    sections.push({
      title: 'Compliance Information',
      data: createSummaryData(extractedData.ComplianceDetails),
      priority: 4
    });
  }

  // 5. Package Information
  if (extractedData.Package) {
    const packageData = createSummaryData(extractedData.Package, ['DimensionDetails']);

    // Add dimensional details if they exist
    if (extractedData.Package.DimensionDetails) {
      Object.entries(extractedData.Package.DimensionDetails).forEach(([dimKey, dimValue]) => {
        if (dimValue && typeof dimValue === 'object') {
          Object.entries(dimValue).forEach(([subKey, subValue]) => {
            packageData.push({
              Property: `${formatPropertyName(dimKey)} (${subKey})`,
              Value: formatValue(subValue)
            });
          });
        }
      });
    }

    sections.push({
      title: 'Package Information',
      data: packageData,
      priority: 5
    });
  }

  // 6. Parametric Features (from Parametric.ParametricsFeatures)
  if (extractedData.Parametric?.ParametricsFeatures && Array.isArray(extractedData.Parametric.ParametricsFeatures)) {
    const parametricData = extractedData.Parametric.ParametricsFeatures.map((feature: any) => ({
      'Feature Name': feature.ParametricFeatureName || 'N/A',
      'Value': feature.ParametricFeatureValue || 'N/A',
      'Normalized': feature.ParametricFeatureNormalized || 'N/A',
      'Unit': feature.ParametricFeatureUnit || 'N/A'
    }));

    sections.push({
      title: 'Parametric Features',
      data: parametricData,
      priority: 6,
      isTabular: true
    });
  }

  // 7. Manufacturing Information
  if (extractedData.Manufacturing) {
    sections.push({
      title: 'Manufacturing Details',
      data: createSummaryData(extractedData.Manufacturing),
      priority: 7
    });
  }

  // 8. Supplier Information
  if (extractedData.SupplierSummary) {
    sections.push({
      title: 'Supplier Information',
      data: createSummaryData(extractedData.SupplierSummary),
      priority: 8
    });
  }

  // 9. Market Availability
  if (extractedData.MarketAvailabilitySummary) {
    sections.push({
      title: 'Market Availability',
      data: createSummaryData(extractedData.MarketAvailabilitySummary),
      priority: 9
    });
  }

  // 10. Manufacturing Locations
  if (extractedData.ManufacturingLocations?.ManufacturingLocations && Array.isArray(extractedData.ManufacturingLocations.ManufacturingLocations)) {
    sections.push({
      title: 'Manufacturing Locations',
      data: extractedData.ManufacturingLocations.ManufacturingLocations.map((location: any) => ({
        'Facility Type': location.FacilityType || location.Facilitytype || 'N/A',
        'Country': location.CountryName || 'N/A',
        'State/Province': location.StateProvinceName || 'N/A',
        'City': location.CityName || 'N/A',
        'Site Owner': location.SiteOwner || 'N/A',
        'Display Name': location.DisplayName || 'N/A',
        'Trust Level': location.TrustLevel || 'N/A'
      })),
      priority: 10,
      isTabular: true
    });
  }

  // 11. Trade Codes
  if (extractedData.TradeCodes?.TradeCodes && Array.isArray(extractedData.TradeCodes.TradeCodes)) {
    sections.push({
      title: 'Trade Codes',
      data: extractedData.TradeCodes.TradeCodes.map((trade: any) => ({
        'Code Name': trade.TradeCodeName || 'N/A',
        'Code Value': trade.TradeCodeValue || 'N/A'
      })),
      priority: 11,
      isTabular: true
    });
  }

  // 12. PCN History
  if (extractedData.PCNHistory && Array.isArray(extractedData.PCNHistory)) {
    sections.push({
      title: 'PCN History',
      data: extractedData.PCNHistory.map((pcn: any) => ({
        'Tracking Number': pcn.TrackingNumber || 'N/A',
        'Type Of Changes': Array.isArray(pcn.TypeOfChanges) ? pcn.TypeOfChanges.join(', ') : (pcn.TypeOfChanges || 'N/A'),
        'Notification Date': pcn.NotificationDate || 'N/A',
        'Effective Date': pcn.EffectiveDate || 'N/A',
        'Change Description': pcn.ChangeDescription || 'N/A',
        'Reason Of Change': pcn.ReasonOfChange || 'N/A',
        'Replacement Part': pcn.ReplacementPart || 'N/A',
        'Replacement Company': pcn.ReplacementCompany || 'N/A'
      })),
      priority: 12,
      isTabular: true
    });
  }

  // 13. GIDEP Information
  if (extractedData.GIDEP && Array.isArray(extractedData.GIDEP)) {
    sections.push({
      title: 'GIDEP Records',
      data: extractedData.GIDEP.map((gidep: any) => ({
        'GIDEP No': gidep.GIDEPNo || 'N/A',
        'Date': gidep.Date || 'N/A',
        'Type Of Changes': Array.isArray(gidep.TypeOfChanges) ? gidep.TypeOfChanges.join(', ') : (gidep.TypeOfChanges || 'N/A'),
        'Notification Date': gidep.NotificationDate || 'N/A',
        'Effective Date': gidep.EffectiveDate || 'N/A',
        'Change Description': gidep.ChangeDescription || 'N/A'
      })),
      priority: 13,
      isTabular: true
    });
  }

  // 14. Conflict Mineral Information
  if (extractedData.ConflictMineral || extractedData.PartConflictMineral) {
    const conflictData = [];

    if (extractedData.ConflictMineral) {
      conflictData.push({
        Property: 'General Conflict Mineral Status',
        Value: extractedData.ConflictMineral.ConflictMineralStatus || 'N/A'
      });
      conflictData.push({
        Property: 'Source Type',
        Value: extractedData.ConflictMineral.ConflictMineralSourceType || 'N/A'
      });
    }

    if (extractedData.PartConflictMineral) {
      conflictData.push({
        Property: 'Part Conflict Mineral Status',
        Value: extractedData.PartConflictMineral.ConflictMineralStatus || 'N/A'
      });
      if (extractedData.PartConflictMineral.CountSmelters) {
        conflictData.push({
          Property: 'Smelter Count',
          Value: String(extractedData.PartConflictMineral.CountSmelters)
        });
      }
    }

    if (conflictData.length > 0) {
      sections.push({
        title: 'Conflict Mineral Information',
        data: conflictData,
        priority: 14
      });
    }
  }

  // Sort sections by priority
  sections.sort((a, b) => a.priority - b.priority);

  if (sections.length === 0) {
    // Don't show "No part details data" message during enrichment operations
    // Only show it if the user explicitly searched for part details
    if (!userQuery || userQuery.toLowerCase().includes('enrich')) {
      return null; // Don't render anything for enrichment operations
    }
    return (
      <div className="part-details-container">
        <p>No part details data available to display.</p>
      </div>
    );
  }

  return (
    <div className="part-details-comprehensive">
      <div className="part-details-header">
        <h3>{extractedData.MPNSummary?.MPN || 'Part Details'}</h3>
        <p className="part-details-subtitle">
          {extractedData.MPNSummary?.Supplier || extractedData.SupplierSummary?.SupplierName || 'Component Information'}
        </p>
      </div>

      {sections.map((section, index) => (
        <div key={index} className="part-details-section">
          <TanStackDataTable
            data={{ results: section.data }}
            title={section.title}
            toolName="part_details_section"
            isPartDetailsSection={true}
          />
        </div>
      ))}
    </div>
  );
};

export default PartDetailsDisplay;
export function formatDisplayName(value) {
  if (!value) return 'Non disponibile'

  return String(value)
    .replace(/^(brand|note|accord|perfumer|perfume)_/i, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLocaleLowerCase('it-IT')
    .replace(/(^|\s)(\p{L})/gu, (_, prefix, letter) => `${prefix}${letter.toLocaleUpperCase('it-IT')}`)
}

export function formatGender(value) {
  return {
    men: 'Uomo',
    women: 'Donna',
    unisex: 'Unisex',
  }[value] || formatDisplayName(value)
}

export function getAccordColor(accord, fallback = '#A98C72') {
  return accord?.color_hex || fallback
}

export function createReferenceMaps(references = {}) {
  return {
    brands: new Map((references.brands || []).map((item) => [item._id, item])),
    accords: new Map((references.accords || []).map((item) => [item._id, item])),
  }
}

export function enrichPerfume(perfume, maps) {
  if (!perfume) return perfume
  return {
    ...perfume,
    brand: perfume.brand || maps.brands.get(perfume.brand_id) || null,
    accords: perfume.accords?.length
      ? perfume.accords
      : (perfume.accord_ids || []).map((id) => maps.accords.get(id)).filter(Boolean),
  }
}

export function isDarkColor(hex) {
  const normalized = hex?.replace('#', '')
  if (!normalized || !/^[0-9a-f]{6}$/i.test(normalized)) return false
  const [r, g, b] = [0, 2, 4].map((index) => parseInt(normalized.slice(index, index + 2), 16))
  return (r * 299 + g * 587 + b * 114) / 1000 < 145
}

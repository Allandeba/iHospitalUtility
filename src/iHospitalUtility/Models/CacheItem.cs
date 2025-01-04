namespace iHospitalUtility.Models
{
    public class CacheItem
    {
        public string Value { get; init; } = null!;
        public DateOnly ExpiresAt { get; init; }
    }
}

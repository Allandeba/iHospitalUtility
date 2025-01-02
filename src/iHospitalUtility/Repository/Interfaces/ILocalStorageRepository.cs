namespace iHospitalUtility.Repository.Interfaces
{
    public interface ILocalStorageRepository
    {
        Task SetItemAsync<T>(string itemKey, T value, DateOnly expiresAt);
        Task SetItemAsync<T>(string itemKey, T value);
        Task<T?> GetItemAsync<T>(string itemKey);
        Task RemoveItemAsync(string itemKey);
    }
}